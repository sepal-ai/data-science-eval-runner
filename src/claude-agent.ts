import Anthropic from '@anthropic-ai/sdk';
import { ComputerUseMCP } from './computer-use-mcp.js';
import fs from 'fs';
import { ANTHROPIC_API_KEY, SEPAL_AI_API_KEY } from './env.js';

// Constants

const THINKING_SUPPORTED_MODELS = [
  'claude-opus-4-20250514',
  'claude-sonnet-4-20250514',
  'claude-3-7-sonnet-20250219'
];

interface RunAgentParams {
  model: string;
  machineSnapshotId: string;
  taskPrompt: string;
  systemPrompt: string;
  thinking: boolean;
  maxIterations: number;
  maxTokens: number;
  eventRelayHandler: (event: any) => Promise<void>;
}

interface MCPToolResult {
  content: Array<{
    type: 'text' | 'image';
    text?: string;
    data?: string;
    mimeType?: string;
  }>;
}

// Agent implementation

export class ClaudeAgent {
  private anthropic: Anthropic;
  private mcp: ComputerUseMCP | null = null;
  private sessionId: string;
  private transcriptDirPath: string;

  constructor() {
    this.anthropic = new Anthropic({
      apiKey: ANTHROPIC_API_KEY!,
    });
    this.sessionId = `session-${Date.now()}`;
    this.transcriptDirPath = `transcripts/${this.sessionId}`;
    if (!fs.existsSync(this.transcriptDirPath)) {
      fs.mkdirSync(this.transcriptDirPath, { recursive: true });
    }
  }

  async runAgent(params: RunAgentParams): Promise<void> {
    const { model, machineSnapshotId, taskPrompt, systemPrompt, thinking, maxIterations, maxTokens, eventRelayHandler } = params;

    try {
      // Initialize MCP connection
      this.mcp = new ComputerUseMCP({
        machineSnapshotId: machineSnapshotId,
        apiKey: SEPAL_AI_API_KEY!,
      });
      // Start the MCP server
      await eventRelayHandler({
        type: 'mcp_server_start',
      });
      const machine = await this.mcp.start();
      await eventRelayHandler({
        type: 'mcp_server_ready',
        machineId: machine.machineId,
        appName: machine.appName,
        vncUrl: machine.vncUrl,
      });

      // Build messages array
      const messages: Anthropic.Messages.MessageParam[] = [
        {
          role: 'user',
          content: taskPrompt,
        },
      ];

      // Start the conversation loop
      await this.conversationLoop({
        model,
        systemPrompt,
        messages,
        thinking,
        maxIterations,
        maxTokens,
        eventRelayHandler,
      });

    } catch (error) {
      await eventRelayHandler({
        type: 'error',
        error: error instanceof Error ? error.message : String(error),
      });
    } finally {
      this.mcp = null;
    }
  }

  private async conversationLoop(params: {
    model: string;
    systemPrompt: string;
    messages: Anthropic.Messages.MessageParam[];
    thinking: boolean;
    maxIterations: number;
    maxTokens: number;
    eventRelayHandler: (event: any) => Promise<void>;
  }): Promise<void> {
    const { model, systemPrompt, messages, thinking, maxIterations, maxTokens, eventRelayHandler } = params;
    // Get available MCP tools
    const tools = this.getMCPTools();

    let iterations = 0;
    while (iterations < maxIterations) {
      iterations++;

      // Create Claude message request
      const messageParams: Anthropic.Messages.MessageCreateParams = {
        model,
        max_tokens: maxTokens,
        system: systemPrompt,
        messages: [...messages],
        ...(tools.length > 0 && { tools }),
        stream: false,
      };

      // Add thinking parameter if supported
      if (thinking && THINKING_SUPPORTED_MODELS.includes(model)) {
        (messageParams as any).thinking = {
          type: 'enabled',
          budget_tokens: Math.max(1024, Math.floor(maxTokens * 0.2)) // At least 1024, or 20% of max tokens
        };
      }

      try {
        // Relay iteration start event
        await eventRelayHandler({
          type: 'iteration_start',
          iteration: iterations,
          maxIterations
        });

        // Make the API call to Claude
        const response = await this.anthropic.messages.create(messageParams);

        // Relay the response event
        await eventRelayHandler({
          type: 'claude_response',
          response: {
            id: response.id,
            model: response.model,
            content: response.content,
            stop_reason: response.stop_reason,
            usage: response.usage
          }
        });

        // Add Claude's response to messages
        messages.push({
          role: 'assistant',
          content: response.content as any
        });

        // Check if we need to handle tool use
        const toolUseBlocks = response.content.filter(block => block.type === 'tool_use');

        if (toolUseBlocks.length > 0) {
          // Process each tool use
          const toolResults: any[] = [];

          for (const toolUse of toolUseBlocks) {
            if (toolUse.type === 'tool_use') {
              try {
                // Relay tool execution start
                await eventRelayHandler({
                  type: 'tool_execution_start',
                  toolName: toolUse.name,
                  toolId: toolUse.id,
                  input: toolUse.input
                });

                // Execute the MCP tool
                const toolResult = await this.executeMCPTool(toolUse.name, toolUse.input);

                // Relay tool execution result
                await eventRelayHandler({
                  type: 'tool_execution_result',
                  toolName: toolUse.name,
                  toolId: toolUse.id,
                  result: toolResult
                });

                // Format tool result for Claude
                const formattedResult = {
                  type: 'tool_result' as const,
                  tool_use_id: toolUse.id,
                  content: Array.isArray(toolResult.content) ?
                    toolResult.content.map(item => {
                      if (item.type === 'text') {
                        return { type: 'text' as const, text: item.text || '' };
                      } else if (item.type === 'image') {
                        // Validate base64 data before sending to Claude
                        if (!item.data || item.data.length === 0) {
                          // If no image data, return text description instead
                          return { type: 'text' as const, text: '[Image data unavailable]' };
                        }
                        return {
                          type: 'image' as const,
                          source: {
                            type: 'base64' as const,
                            media_type: item.mimeType || 'image/png',
                            data: item.data
                          }
                        };
                      }
                      return { type: 'text' as const, text: JSON.stringify(item) };
                    }) :
                    [{ type: 'text' as const, text: typeof toolResult.content === 'string' ? toolResult.content : JSON.stringify(toolResult.content) }]
                };

                toolResults.push(formattedResult);

              } catch (toolError) {
                // Relay tool execution error
                await eventRelayHandler({
                  type: 'tool_execution_error',
                  toolName: toolUse.name,
                  toolId: toolUse.id,
                  error: toolError instanceof Error ? toolError.message : String(toolError)
                });

                // Add error result to continue conversation
                toolResults.push({
                  type: 'tool_result' as const,
                  tool_use_id: toolUse.id,
                  content: [{
                    type: 'text' as const,
                    text: `Tool execution failed: ${toolError instanceof Error ? toolError.message : String(toolError)}`
                  }],
                  is_error: true
                });
              }
            }
          }

          // Add tool results to messages if any tools were executed
          if (toolResults.length > 0) {
            messages.push({
              role: 'user',
              content: toolResults
            });

            // Continue the loop to get Claude's response to the tool results
            continue;
          }
        }

        // Check stop reason to determine if we should continue
        if (response.stop_reason === 'end_turn') {
          // Natural completion
          await eventRelayHandler({
            type: 'completion',
            reason: 'end_turn',
            totalIterations: iterations
          });
          break;
        } else if (response.stop_reason === 'max_tokens') {
          // Hit token limit
          await eventRelayHandler({
            type: 'completion',
            reason: 'max_tokens',
            totalIterations: iterations
          });
          break;
        } else if (response.stop_reason === 'stop_sequence') {
          // Hit stop sequence
          await eventRelayHandler({
            type: 'completion',
            reason: 'stop_sequence',
            totalIterations: iterations
          });
          break;
        }
        // If stop_reason is 'tool_use', we've already handled it above and will continue

      } catch (error) {
        await eventRelayHandler({
          type: 'error',
          error: error instanceof Error ? error.message : String(error),
          iteration: iterations
        });
        throw error;
      }
    }

    // Handle max iterations reached
    if (iterations >= maxIterations) {
      await eventRelayHandler({
        type: 'error',
        error: 'Maximum iterations reached. Task may be incomplete.',
      });
    }
  }

  private getMCPTools(): Anthropic.Tool[] {
    // Return the tools available from the MCP server
    const mcpTools = this.mcp?.getTools() || [];
    return mcpTools.map(tool => ({
      name: tool.name,
      description: tool.description,
      input_schema: tool.inputSchema as any
    }));
  }

  private async executeMCPTool(toolName: string, input: any): Promise<MCPToolResult> {
    if (!this.mcp) {
      throw new Error('MCP connection not initialized');
    }
    return await this.mcp.callTool(toolName, input) as MCPToolResult;
  }
}
