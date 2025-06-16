#!/usr/bin/env node

import * as readline from 'readline/promises';
import * as fs from 'fs/promises';
import * as path from 'path';
import { ClaudeAgent, DEFAULT_SYSTEM_PROMPT } from './claude-agent.js';
import { MachineCatalog, SepalUtilities } from './sepal-utilities.js';
import { SEPAL_AI_API_KEY } from './env.js';

// ANSI color codes for better output formatting
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m'
};

interface CLIInputs {
  model: string;
  machineSnapshotId: string;
  machineShortName: string;
  taskPrompt: string;
  systemPrompt: string;
  thinking: boolean;
  maxIterations: number;
  maxTokens: number;
}

interface TranscriptEvent {
  timestamp: string;
  type: string;
  data: any;
  screenshotIds?: string[];
}

class ClaudeCLI {
  private rl: readline.Interface;
  private sessionId: string;
  private transcriptDir: string;
  private transcript: TranscriptEvent[] = [];
  private nextScreenshotId: number = 1;
  private machineId: string | null = null;
  private sepal: SepalUtilities;

  constructor() {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });
    this.sepal = new SepalUtilities(SEPAL_AI_API_KEY);

    // Generate session ID using timestamp
    this.sessionId = `session-${Date.now()}`;
    this.transcriptDir = path.join('transcripts', this.sessionId);
  }

  private async ensureTranscriptDir(): Promise<void> {
    try {
      await fs.mkdir(this.transcriptDir, { recursive: true });
    } catch (error) {
      console.error(`Failed to create transcript directory: ${error}`);
      throw error;
    }
  }

  private getFileExtensionFromMimeType(mimeType: string): string {
    const mimeToExt: { [key: string]: string } = {
      'image/png': 'png',
      'image/jpeg': 'jpg',
      'image/jpg': 'jpg',
      'image/gif': 'gif',
      'image/webp': 'webp',
      'image/bmp': 'bmp',
      'image/svg+xml': 'svg'
    };
    return mimeToExt[mimeType] || 'png'; // default to png
  }

  private async saveScreenshot(imageData: any, mimeType: string): Promise<string> {
    const screenshotId = this.nextScreenshotId++;
    const extension = this.getFileExtensionFromMimeType(mimeType);
    const filename = `screenshot-${screenshotId}.${extension}`;
    const filepath = path.join(this.transcriptDir, filename);

    try {
      // If imageData is base64 encoded, decode it
      let binaryData: Buffer;
      if (typeof imageData === 'string') {
        // Remove data URL prefix if present (e.g., "data:image/png;base64,")
        const base64Data = imageData.replace(/^data:image\/[a-z]+;base64,/, '');
        binaryData = Buffer.from(base64Data, 'base64');
      } else if (Buffer.isBuffer(imageData)) {
        binaryData = imageData;
      } else {
        // Fallback: try to convert to string and then to buffer
        binaryData = Buffer.from(String(imageData), 'base64');
      }

      await fs.writeFile(filepath, binaryData);
      return filename;
    } catch (error) {
      console.error(`Failed to save screenshot ${screenshotId}: ${error}`);
      throw error;
    }
  }

  private async saveTranscript(): Promise<void> {
    const transcriptPath = path.join(this.transcriptDir, 'transcript.json');
    const transcriptData = {
      sessionId: this.sessionId,
      startTime: this.transcript[0]?.timestamp || new Date().toISOString(),
      endTime: new Date().toISOString(),
      events: this.transcript
    };

    try {
      await fs.writeFile(transcriptPath, JSON.stringify(transcriptData, null, 2));
      this.log(`\n📄 Transcript saved to: ${transcriptPath}`, colors.bright + colors.blue);
    } catch (error) {
      console.error(`Failed to save transcript: ${error}`);
      throw error;
    }
  }

  private log(message: string, color: string = colors.reset): void {
    console.log(`${color}${message}${colors.reset}`);
  }

  private async promptUser(): Promise<CLIInputs> {
    this.log('\n=== Claude Agent CLI ===\n', colors.bright + colors.cyan);

    // Model selection
    const model = await this.rl.question(
      `${colors.yellow}Enter Claude model${colors.reset} (default: claude-opus-4-20250514): `
    ) || 'claude-opus-4-20250514';

    // Get machine catalog
    this.log('\n🔍 Fetching available machines...', colors.yellow);
    let machines: MachineCatalog[];

    try {
      machines = await this.sepal.listMachineCatalogs();

      if (!machines || machines.length === 0) {
        throw new Error('No machines available');
      }

      // Display available machines
      this.log('\n📋 Available machines:', colors.bright + colors.cyan);
      machines.forEach((machine, index) => {
        this.log(`\n${colors.bright}[${index + 1}]${colors.reset} ${colors.green}${machine.taskShortName}${colors.reset}`);
        this.log(`    Type: ${machine.machineType}`, colors.gray);
        this.log(`    Description: ${machine.taskDescription.substring(0, 100)}...`, colors.gray);
        this.log(`    ID: ${machine.id}`, colors.gray);
      });

      // Ask user to select a machine
      let selectedIndex: number;
      while (true) {
        const selection = await this.rl.question(
          `\n${colors.yellow}Select a machine (1-${machines.length}):${colors.reset} `
        );
        selectedIndex = parseInt(selection) - 1;

        if (selectedIndex >= 0 && selectedIndex < machines.length) {
          break;
        }
        this.log('❌ Invalid selection. Please try again.', colors.red);
      }

      const selectedMachine = machines[selectedIndex];
      if (!selectedMachine) {
        throw new Error('No machine selected');
      }
      this.log(`\n✅ Selected: ${selectedMachine.taskShortName}`, colors.green);

      var machineSnapshotId = selectedMachine.id;
      var machineShortName = selectedMachine.taskShortName;
      var machineDescription = selectedMachine.taskDescription;

    } catch (error) {
      this.log(`\n❌ Failed to fetch machine catalog: ${error}`, colors.red);
      throw error;
    }

    // Task prompt
    this.log('\nDefault task prompt:', colors.gray);
    this.log(machineDescription, colors.gray);
    const useDefaultTaskPrompt = (await this.rl.question(
      `\n${colors.yellow}Use default task prompt shown above?${colors.reset} (Y/n): `
    )).toLowerCase() !== 'n';

    let taskPrompt: string;
    if (useDefaultTaskPrompt) {
      taskPrompt = machineDescription;
      this.log('Using default task prompt ✓', colors.green);
    } else {
      this.log('\nEnter your custom task prompt (press Enter twice when done):', colors.yellow);
      const taskPromptInput = await this.multiLineInput();
      taskPrompt = taskPromptInput.trim() || machineDescription; // Fallback to default if empty
      if (!taskPromptInput.trim()) {
        this.log('Empty input - falling back to default task prompt:', colors.gray);
        this.log(machineDescription, colors.gray);
      }
    }

    // System prompt
    this.log('\nDefault system prompt:', colors.gray);
    this.log(DEFAULT_SYSTEM_PROMPT, colors.gray);
    const useDefaultSystemPrompt = (await this.rl.question(
      `\n${colors.yellow}Use default system prompt shown above?${colors.reset} (Y/n): `
    )).toLowerCase() !== 'n';

    let systemPrompt: string;
    if (useDefaultSystemPrompt) {
      systemPrompt = DEFAULT_SYSTEM_PROMPT;
      this.log('Using default system prompt ✓', colors.green);
    } else {
      this.log('\nEnter your custom system prompt (press Enter twice when done):', colors.yellow);
      const systemPromptInput = await this.multiLineInput();
      systemPrompt = systemPromptInput.trim() || DEFAULT_SYSTEM_PROMPT; // Fallback to default if empty
      if (!systemPromptInput.trim()) {
        this.log('Empty input - falling back to default system prompt:', colors.gray);
        this.log(DEFAULT_SYSTEM_PROMPT, colors.gray);
      }
    }

    // Thinking mode
    const thinkingInput = await this.rl.question(
      `${colors.yellow}Enable thinking mode?${colors.reset} (Y/n): `
    );
    const thinking = !thinkingInput.toLowerCase().startsWith('n');

    // Max iterations
    const maxIterationsInput = await this.rl.question(
      `${colors.yellow}Maximum iterations${colors.reset} (default: 500): `
    );
    const maxIterations = parseInt(maxIterationsInput) || 500;

    // Max tokens
    const maxTokensInput = await this.rl.question(
      `${colors.yellow}Maximum tokens${colors.reset} (default: 8192): `
    );
    const maxTokens = parseInt(maxTokensInput) || 8192;

    return {
      model,
      machineSnapshotId,
      machineShortName,
      taskPrompt,
      systemPrompt,
      thinking,
      maxIterations,
      maxTokens
    };
  }

  private async multiLineInput(): Promise<string> {
    const lines: string[] = [];
    let emptyLineCount = 0;

    while (true) {
      const line = await this.rl.question('> ');

      if (line.trim() === '') {
        emptyLineCount++;
        if (emptyLineCount >= 2) {
          break;
        }
        lines.push(line);
      } else {
        emptyLineCount = 0;
        lines.push(line);
      }
    }

    // Remove trailing empty lines
    while (lines.length > 0 && lines[lines.length - 1]?.trim() === '') {
      lines.pop();
    }

    return lines.join('\n');
  }

  private async eventRelayHandler(event: any): Promise<void> {
    const timestamp = new Date().toISOString();
    const screenshots: string[] = [];

    // Create a deep copy of the event for the transcript
    const transcriptEventData = JSON.parse(JSON.stringify(event));

    // Process any images in the event and save them separately
    if (event.type === 'tool_execution_result' && event.result?.content) {
      for (let i = 0; i < event.result.content.length; i++) {
        const item = event.result.content[i];
        if (item.type === 'image') {
          try {
            const filename = await this.saveScreenshot(item.data, item.mimeType);
            screenshots.push(filename);
            // Replace image data with reference in the TRANSCRIPT copy only
            if (transcriptEventData.result?.content?.[i]) {
              transcriptEventData.result.content[i].data = `[Screenshot saved as ${filename}]`;
            }
          } catch (error) {
            console.error(`Failed to save screenshot: ${error}`);
          }
        }
      }
    }

    // Add event to transcript
    const transcriptEvent: TranscriptEvent = {
      timestamp,
      type: event.type,
      data: transcriptEventData,
      ...(screenshots.length > 0 && { screenshots: screenshots })
    };

    this.transcript.push(transcriptEvent);

    // Display the event (existing logic)
    const displayTimestamp = new Date().toLocaleTimeString();

    switch (event.type) {
      case 'mcp_server_start':
        this.log(
          `\n[${displayTimestamp}] 🚀 Starting MCP server...`,
          colors.bright + colors.yellow
        );
        break;

      case 'mcp_server_ready':
        this.log(
          `[${displayTimestamp}] ✅ MCP server ready! Machine Name: ${event.appName} (${event.machineId})`,
          colors.bright + colors.green
        );
        if (event.vncUrl) {
          this.log(
            `[${displayTimestamp}] 🖥️  View the agent in action at: ${event.vncUrl}`,
            colors.bright + colors.yellow
          );
        }
        // Store the machineId for later use
        if (event.machineId) {
          this.machineId = event.machineId;
        }
        break;

      case 'iteration_start':
        this.log(
          `\n[${displayTimestamp}] 🔄 Starting iteration ${event.iteration}/${event.maxIterations}`,
          colors.bright + colors.blue
        );
        break;

      case 'claude_response':
        this.log(`\n[${displayTimestamp}] 🤖 Claude Response:`, colors.bright + colors.green);
        this.log(`  Model: ${event.response.model}`, colors.gray);
        this.log(`  Stop Reason: ${event.response.stop_reason}`, colors.gray);
        this.log(`  Usage: ${JSON.stringify(event.response.usage)}`, colors.gray);

        // Display content
        if (event.response.content && Array.isArray(event.response.content)) {
          for (const block of event.response.content) {
            if (block.type === 'text') {
              this.log(`\n${block.text}`, colors.reset);
            } else if (block.type === 'tool_use') {
              this.log(`\n🔧 Tool Use: ${block.name}`, colors.yellow);
              this.log(`  Input: ${JSON.stringify(block.input, null, 2)}`, colors.gray);
            } else if (block.type === 'image') {
              this.log(`\n📷 Image: [Screenshot data saved separately]`, colors.cyan);
            }
          }
        }
        break;

      case 'tool_execution_start':
        this.log(
          `\n[${displayTimestamp}] ⚡ Executing tool: ${event.toolName}`,
          colors.bright + colors.magenta
        );
        this.log(`  Tool ID: ${event.toolId}`, colors.gray);
        this.log(`  Input: ${JSON.stringify(event.input, null, 2)}`, colors.gray);
        break;

      case 'tool_execution_result':
        this.log(
          `[${displayTimestamp}] ✅ Tool execution completed: ${event.toolName}`,
          colors.green
        );

        // Display result content
        if (event.result && event.result.content) {
          for (const item of event.result.content) {
            if (item.type === 'text') {
              this.log(`  Result: ${item.text}`, colors.gray);
            } else if (item.type === 'image') {
              this.log(`  Result: [Image data saved as screenshot]`, colors.cyan);
            }
          }
        }

        if (screenshots.length > 0) {
          this.log(`  📷 Screenshots saved: ${screenshots.join(', ')}`, colors.cyan);
        }
        break;

      case 'tool_execution_error':
        this.log(
          `[${displayTimestamp}] ❌ Tool execution failed: ${event.toolName}`,
          colors.red
        );
        this.log(`  Error: ${event.error}`, colors.red);
        break;

      case 'completion':
        this.log(
          `\n[${displayTimestamp}] 🎉 Task completed!`,
          colors.bright + colors.green
        );
        this.log(`  Reason: ${event.reason}`, colors.gray);
        this.log(`  Total iterations: ${event.totalIterations}`, colors.gray);
        break;

      case 'error':
        this.log(
          `\n[${displayTimestamp}] ❌ Error occurred:`,
          colors.bright + colors.red
        );
        this.log(`  ${event.error}`, colors.red);
        if (event.iteration) {
          this.log(`  At iteration: ${event.iteration}`, colors.gray);
        }
        break;

      default:
        this.log(
          `[${displayTimestamp}] 📄 Unknown event: ${event.type}`,
          colors.gray
        );
        this.log(`  Data: ${JSON.stringify(event, null, 2)}`, colors.gray);
        break;
    }
  }

  async run(): Promise<void> {
    try {
      // Ensure transcript directory exists
      await this.ensureTranscriptDir();
      this.log(`📁 Session ID: ${this.sessionId}`, colors.bright + colors.blue);
      this.log(`📂 Transcript will be saved to: ${this.transcriptDir}`, colors.gray);

      // Get user inputs
      const inputs = await this.promptUser();

      // Display configuration
      this.log('\n=== Configuration ===', colors.bright + colors.cyan);
      this.log(`Model: ${inputs.model}`, colors.gray);
      this.log(`Machine Type: ${inputs.machineShortName}`, colors.gray);
      this.log(`Thinking Mode: ${inputs.thinking ? 'Enabled' : 'Disabled'}`, colors.gray);
      this.log(`Max Iterations: ${inputs.maxIterations}`, colors.gray);
      this.log(`Max Tokens: ${inputs.maxTokens}`, colors.gray);
      this.log(`Task Prompt: ${inputs.taskPrompt.substring(0, 100)}...`, colors.gray);
      this.log(`System Prompt: ${inputs.systemPrompt.substring(0, 100)}...`, colors.gray);

      // Add configuration to transcript
      this.transcript.push({
        timestamp: new Date().toISOString(),
        type: 'session_config',
        data: inputs
      });

      // Confirm before starting
      const confirm = await this.rl.question(
        `\n${colors.yellow}Start the agent?${colors.reset} (Y/n): `
      );

      if (confirm.toLowerCase() === 'n') {
        this.log('Cancelled.', colors.yellow);
        this.transcript.push({
          timestamp: new Date().toISOString(),
          type: 'session_cancelled',
          data: { reason: 'User cancelled' }
        });
        await this.saveTranscript();
        return;
      }

      this.log('\n=== Agent Execution ===', colors.bright + colors.cyan);

      // Create and run the agent
      const agent = new ClaudeAgent();
      await agent.runAgent({
        model: inputs.model,
        machineSnapshotId: inputs.machineSnapshotId,
        taskPrompt: inputs.taskPrompt,
        systemPrompt: inputs.systemPrompt,
        thinking: inputs.thinking,
        maxIterations: inputs.maxIterations,
        maxTokens: inputs.maxTokens,
        eventRelayHandler: this.eventRelayHandler.bind(this)
      });

      // Check goal state reached
      if (this.machineId) {
        this.log('\n=== Checking Goal State ===', colors.bright + colors.cyan);
        try {
          const goalStateResults = await this.sepal.checkGoalStateReached(this.machineId);

          // Display results
          this.log('\n📊 Goal State Check Results:', colors.bright + colors.green);
          let allGoalsReached = true;

          for (const result of goalStateResults) {
            const status = result.goalReached ? '✅' : '❌';
            const statusColor = result.goalReached ? colors.green : colors.red;

            this.log(`\n${status} File: ${result.filePath}`, statusColor);
            this.log(`  Goal Reached: ${result.goalReached}`, colors.gray);
            this.log(`  Diff Length: ${result.diffLength === null ? 'N/A' : result.diffLength}`, colors.gray);
            this.log(`  Note: ${result.note}`, colors.gray);

            if (!result.goalReached) {
              allGoalsReached = false;
            }
          }

          const overallStatus = allGoalsReached ? '✅ All goals reached!' : '❌ Some goals not reached';
          const overallColor = allGoalsReached ? colors.bright + colors.green : colors.bright + colors.red;
          this.log(`\n${overallStatus}`, overallColor);

          // Add goal state results to transcript
          this.transcript.push({
            timestamp: new Date().toISOString(),
            type: 'goal_state_check',
            data: {
              results: goalStateResults,
              allGoalsReached: allGoalsReached
            }
          });

        } catch (error) {
          this.log(
            `\n❌ Failed to check goal state: ${error instanceof Error ? error.message : String(error)}`,
            colors.red
          );

          // Add error to transcript
          this.transcript.push({
            timestamp: new Date().toISOString(),
            type: 'goal_state_check_error',
            data: {
              error: error instanceof Error ? error.message : String(error)
            }
          });
        }
      } else {
        this.log('\n⚠️  Warning: Machine ID not available, skipping goal state check', colors.yellow);
      }

      // Save transcript at the end of successful execution
      await this.saveTranscript();

    } catch (error) {
      this.log(
        `\n❌ Fatal error: ${error instanceof Error ? error.message : String(error)}`,
        colors.bright + colors.red
      );

      // Add error to transcript
      this.transcript.push({
        timestamp: new Date().toISOString(),
        type: 'fatal_error',
        data: {
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined
        }
      });

      // Still save transcript even if there was an error
      try {
        await this.saveTranscript();
      } catch (saveError) {
        console.error('Failed to save transcript after error:', saveError);
      }

      // Let the error propagate up to main() for consistent error handling
      throw error;

    } finally {
      if (this.machineId) {
        this.log('\n=== Shutting Down Machine ===', colors.bright + colors.cyan);
        try {
          const shutdownResult = await this.sepal.shutdownMachine(this.machineId);
          this.log(`✅ Machine shutdown successful: ${shutdownResult.status}`, colors.green);
        } catch (error) {
          this.log(
            `\n❌ Failed to shutdown machine: ${error instanceof Error ? error.message : String(error)}`,
            colors.red
          );
        }
      }
      this.rl.close();
    }
  }
}

// Main execution
async function main() {
  const cli = new ClaudeCLI();
  try {
    await cli.run();
  } catch (error) {
    process.exit(1);
  }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n👋 Goodbye!');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n\n👋 Goodbye!');
  process.exit(0);
});

main();
