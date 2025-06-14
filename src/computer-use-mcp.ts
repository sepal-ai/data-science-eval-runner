import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
  CallToolRequest,
} from "@modelcontextprotocol/sdk/types.js";
import axios, { AxiosRequestConfig } from "axios";

const BASE_URL = "https://api.nexus.sepalai.com/openapi/eval-machines"

interface ComputerUseMCPConfig {
  machineSnapshotId: string;
  apiKey: string;
}

export class ComputerUseMCP {
  private server: Server;
  private machineSnapshotId: string;
  private apiKey: string;
  private machineId: string | null = null;

  constructor(config: ComputerUseMCPConfig) {
    this.machineSnapshotId = config.machineSnapshotId;
    this.apiKey = config.apiKey;
    this.server = new Server(
      {
        name: "computer-use",
        version: "0.1.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
  }

  /**
   * Initializes the computer use MCP by creating a machine instance.
   * This method must be called before using any tools.
   * 
   * @returns {Promise<void>} Promise that resolves when the machine is created and ready
   */
  async start() {
    const machine = await this.createMachine(this.machineSnapshotId);
    this.machineId = machine.machineId;
    // Wait for the MCP server to be ready (max 1 minute)
    const startTime = Date.now();
    const timeoutMs = 180 * 1000; // 3 minute timeout
    while (true) {
      const status = await this.getMachineStatus();
      if (status.status === 'deployed') {
        break;
      }
      if (Date.now() - startTime > timeoutMs) {
        throw new McpError(
          ErrorCode.InternalError,
          `Timed out waiting for machine to be ready after ${timeoutMs / 1000} seconds`
        );
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    // Wait for another 5 seconds to make sure the machine is ready
    await new Promise(resolve => setTimeout(resolve, 5000));
    return machine;
  }

  /**
   * Returns the list of available tools that can be called via the MCP interface.
   * Each tool includes its name, description, and input schema for validation.
   * 
   * @returns {Array<Object>} Array of tool definitions with schemas
   */
  getTools() {
    return [
      {
        name: "move_mouse",
        description: "Move mouse cursor to absolute coordinates (x, y)",
        inputSchema: {
          type: "object",
          properties: {
            x: {
              type: "number",
              description: "X coordinate to move mouse to",
            },
            y: {
              type: "number",
              description: "Y coordinate to move mouse to",
            },
          },
          required: ["x", "y"],
        },
      },
      {
        name: "drag_mouse",
        description: "Drag mouse to coordinates (x, y) over optional duration",
        inputSchema: {
          type: "object",
          properties: {
            x: {
              type: "number",
              description: "X coordinate to drag mouse to",
            },
            y: {
              type: "number",
              description: "Y coordinate to drag mouse to",
            },
            duration: {
              type: "number",
              description: "Duration of drag in seconds (optional, default 0.0)",
            },
          },
          required: ["x", "y"],
        },
      },
      {
        name: "left_click",
        description: "Left click mouse at current position",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "right_click",
        description: "Right click mouse at current position",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "type_text",
        description: "Type the given text string",
        inputSchema: {
          type: "object",
          properties: {
            text: {
              type: "string",
              description: "Text to type",
            },
          },
          required: ["text"],
        },
      },
      {
        name: "press_key",
        description: "Press a single key. Supports letters (a-z), numbers (0-9), symbols/punctuation, function keys (f1-f24), navigation keys (up, down, left, right, home, end, pageup, pagedown), special keys (enter, escape, tab, space, backspace, delete, insert), etc.",
        inputSchema: {
          type: "object",
          properties: {
            key: {
              type: "string",
              description: "Single key to press (e.g., 'a', 'enter', 'tab', 'f1')",
            },
            presses: {
              type: "number",
              description: "Number of times to press the key (default: 1)",
              minimum: 1,
            },
          },
          required: ["key"],
        },
      },
      {
        name: "hotkey",
        description: "Press a key combination. Use '+' to separate keys (e.g., 'ctrl+c', 'shift+v'). Supports modifier keys (ctrl, alt, shift, win, command, option) combined with other keys.",
        inputSchema: {
          type: "object",
          properties: {
            combination: {
              type: "string",
              description: "Key combination to press (e.g., 'ctrl+c', 'cmd+v', 'alt+tab')",
            },
          },
          required: ["combination"],
        },
      },
      {
        name: "get_current_position",
        description: "Get the current mouse cursor position",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "get_system_info",
        description: "Get system information including IP, screen resolution, cursor position, and active windows",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "get_screenshot",
        description: "Take a screenshot of the entire screen and return it as base64 encoded image. If the cursor is visible, it will be included in the screenshot as a red crosshair.",
        inputSchema: {
          type: "object",
          properties: {
            format: {
              type: "string",
              enum: ["png", "jpeg"],
              description: "Image format (default: png)",
            },
          },
          required: [],
        },
      },
      {
        name: "get_regional_screenshot",
        description: "Take a screenshot of a specific region and return it as base64 encoded image. If the cursor is visible, it will be included in the screenshot as a red crosshair.",
        inputSchema: {
          type: "object",
          properties: {
            x: {
              type: "number",
              description: "X coordinate of region to capture",
            },
            y: {
              type: "number",
              description: "Y coordinate of region to capture",
            },
            width: {
              type: "number",
              description: "Width of region to capture",
            },
            height: {
              type: "number",
              description: "Height of region to capture",
            },
            format: {
              type: "string",
              enum: ["png", "jpeg"],
              description: "Image format (default: png)",
            },
          },
          required: [],
        },
      },
      {
        name: "get_screen_size",
        description: "Get the screen resolution (width and height) in pixels",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
    ];
  }

  /**
   * Executes a tool with the provided arguments.
   * This is the main entry point for tool execution in the MCP protocol.
   * 
   * @param {string} toolName - The name of the tool to execute
   * @param {any} args - Arguments to pass to the tool (must match tool's input schema)
   * @returns {Promise<Object>} Promise that resolves to the tool execution result
   */
  async callTool(toolName: string, args: any) {
    switch (toolName) {
      case "move_mouse":
        return await this.moveMouse(args as { x: number; y: number });
      case "drag_mouse":
        return await this.dragMouse(args as { x: number; y: number; duration?: number });
      case "left_click":
        return await this.leftClick();
      case "right_click":
        return await this.rightClick();
      case "type_text":
        return await this.typeText(args as { text: string });
      case "press_key":
        return await this.pressKey(args as { key: string; presses?: number });
      case "hotkey":
        return await this.hotkey(args as { combination: string });
      case "get_current_position":
        return await this.getCurrentPosition();
      case "get_system_info":
        return await this.getSystemInfo();
      case "get_screenshot":
        return await this.getScreenshot(args as { format?: string });
      case "get_regional_screenshot":
        return await this.getRegionalScreenshot(args as { x: number; y: number; width: number; height: number; format?: string });
      case "get_screen_size":
        return await this.getScreenSize();
      default:
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Unknown tool: ${toolName}`
        );
    }
  }

  /**
   * Connects the MCP server to the stdio transport for communication.
   * This establishes the communication channel between the MCP client and server.
   * 
   * @returns {Promise<void>} Promise that resolves when connection is established
   */
  async connect() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }

  /**
   * Closes the MCP server and cleans up resources.
   * Should be called when the MCP session is ending.
   * 
   * @returns {Promise<void>} Promise that resolves when server is closed
   */
  async close() {
    await this.server.close();
  }

  private async makeRequest(config: AxiosRequestConfig, operation: string): Promise<any> {
    const requestConfig: AxiosRequestConfig = {
      ...config,
      timeout: config.timeout || 30000, // Default 30 second timeout
      validateStatus: function (status) {
        return status >= 200 && status < 300;
      },
    };

    try {
      const response = await axios(requestConfig);
      return response;
    } catch (error) {
      console.error(`Error in ${operation}:`, error);
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to ${operation}: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  private async createMachine(machineSnapshotId: string): Promise<{
    machineId: string,
    appName: string,
    vncUrl: string
  }> {
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machine: {
          snapshotId: machineSnapshotId,
        },
      }),
    };
    const response = await this.makeRequest(config, 'create machine');
    return response.data;
  }

  private async getMachineStatus(): Promise<{
    status: string,
    appName: string
  }> {
    const config: AxiosRequestConfig = {
      method: 'get',
      url: `${BASE_URL}/status?machineId=${this.machineId}`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      }
    };
    const response = await this.makeRequest(config, 'get machine status');
    return response.data;
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, () => {
      return {
        tools: this.getTools(),
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
      const { name, arguments: args } = request.params;
      try {
        if (!args) {
          throw new McpError(
            ErrorCode.InvalidParams,
            "Tool arguments are required"
          );
        }
        return await this.callTool(name, args);
      } catch (error) {
        if (error instanceof McpError) {
          throw error;
        }
        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${error instanceof Error ? error.message : String(error)}`
        );
      }
    });
  }

  private async moveMouse(args: { x: number, y: number }) {
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/mouse/move`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: this.machineId,
        x: args.x,
        y: args.y,
      }),
    };
    const response = await this.makeRequest(config, 'move mouse');
    return {
      content: [
        {
          type: "text",
          text: `Mouse moved to (${response.data.x}, ${response.data.y})`,
        },
      ],
    };
  }

  private async dragMouse(args: { x: number, y: number, duration?: number }) {
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/mouse/drag`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: this.machineId,
        x: args.x,
        y: args.y,
        duration: args.duration || 1.0,
      }),
    };
    const response = await this.makeRequest(config, 'drag mouse');
    return {
      content: [
        {
          type: "text",
          text: `Mouse dragged to (${response.data.x}, ${response.data.y}) over ${response.data.duration}s`,
        },
      ],
    };
  }

  private async leftClick() {
    const data: Record<string, any> = { button: 'left' };
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/mouse/click`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: this.machineId,
        ...data,
      }),
    };
    const response = await this.makeRequest(config, 'left click mouse');
    return {
      content: [
        {
          type: "text",
          text: `Left clicked at (${response.data.x}, ${response.data.y})`,
        },
      ],
    };
  }

  private async rightClick() {
    const data: Record<string, any> = { button: 'right' };
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/mouse/click`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: this.machineId,
        ...data,
      }),
    };
    const response = await this.makeRequest(config, 'right click mouse');
    return {
      content: [
        {
          type: "text",
          text: `Right clicked at (${response.data.x}, ${response.data.y})`,
        },
      ],
    };
  }

  private async typeText(args: { text: string }) {
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/keyboard/type`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: this.machineId,
        text: args.text,
      }),
    };

    const response = await this.makeRequest(config, 'type text');
    return {
      content: [
        {
          type: "text",
          text: `Typed: "${response.data.text}"`,
        },
      ],
    };
  }

  private async pressKey(args: { key: string, presses?: number }) {
    // Validate that it's a single key, not a combination
    if (args.key.includes('+')) {
      throw new McpError(
        ErrorCode.InvalidParams,
        "press_key is for single keys only. Use hotkey tool for key combinations."
      );
    }
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/keyboard/press`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: this.machineId,
        key: args.key,
        presses: args.presses || 1,
      }),
    };
    const response = await this.makeRequest(config, 'press key');
    return {
      content: [
        {
          type: "text",
          text: `Pressed key: ${response.data.key} (${response.data.presses} time(s))`
        },
      ],
    }
  }

  private async hotkey(args: { combination: string }) {
    // Validate that it's a combination
    if (!args.combination.includes('+')) {
      throw new McpError(
        ErrorCode.InvalidParams,
        "hotkey is for key combinations only. Use press_key tool for single keys."
      );
    }
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/keyboard/press`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: this.machineId,
        key: args.combination,
        presses: 1,
      }),
    };
    const response = await this.makeRequest(config, 'press hotkey');
    return {
      content: [
        {
          type: "text",
          text: `Pressed hotkey: ${response.data.key}`
        },
      ],
    }
  }

  private async getCurrentPosition() {
    if (!this.machineId) {
      throw new McpError(
        ErrorCode.InternalError,
        "Machine ID is not set. Please call start() first."
      );
    }
    const config: AxiosRequestConfig = {
      method: 'get',
      url: `${BASE_URL}/status/current-position?machineId=${encodeURIComponent(this.machineId)}`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
    };
    const response = await this.makeRequest(config, 'get current position');
    return {
      content: [
        {
          type: "text",
          text: `Current mouse position: (${response.data.x}, ${response.data.y})`,
        },
      ],
    };
  }

  private async getSystemInfo() {
    if (!this.machineId) {
      throw new McpError(
        ErrorCode.InternalError,
        "Machine ID is not set. Please call start() first."
      );
    }
    const config: AxiosRequestConfig = {
      method: 'get',
      url: `${BASE_URL}/system/info?machineId=${encodeURIComponent(this.machineId)}`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
    };
    const response = await this.makeRequest(config, 'get system info');
    const info = response.data;
    const systemInfoText = `System Information:
- IP Address: ${info.ip_address}
- Hostname: ${info.hostname}
- Screen Resolution: ${info.screen_resolution.width}x${info.screen_resolution.height}
- Current Cursor Position: (${info.cursor_position.x}, ${info.cursor_position.y})
- Active Window: ${info.active_window.name} (ID: ${info.active_window.id})
- Running Apps: ${info.running_apps.map((app: any) => `${app.name} (PID: ${app.pid})`).join(', ')}`;
    return {
      content: [
        {
          type: "text",
          text: systemInfoText,
        },
      ],
    };
  }

  private async getScreenshot(args: { format?: string }) {
    if (!this.machineId) {
      throw new McpError(
        ErrorCode.InternalError,
        "Machine ID is not set. Please call start() first."
      );
    }
    const params = new URLSearchParams();
    params.append('machineId', this.machineId!);
    if (args.format !== undefined) params.append('format', args.format);
    const config: AxiosRequestConfig = {
      method: 'get',
      url: `${BASE_URL}/screenshot?${params.toString()}`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
    };
    const response = await this.makeRequest(config, 'capture screenshot');
    const base64Data = response.data.data.includes(',') ? response.data.data.split(',')[1] : response.data.data;
    return {
      content: [
        {
          type: "image",
          data: base64Data,
          mimeType: `image/${response.data.format}`,
        },
        {
          type: "text",
          text: `Screenshot captured. Cursor position: (${response.data.cursor_position.x}, ${response.data.cursor_position.y})`,
        },
      ],
    };
  }

  private async getRegionalScreenshot(args: { x: number, y: number, width: number, height: number, format?: string }) {
    if (!this.machineId) {
      throw new McpError(
        ErrorCode.InternalError,
        "Machine ID is not set. Please call start() first."
      );
    }
    const params = new URLSearchParams();
    params.append('machineId', this.machineId!);
    params.append('x', args.x.toString());
    params.append('y', args.y.toString());
    params.append('width', args.width.toString());
    params.append('height', args.height.toString());
    if (args.format !== undefined) params.append('format', args.format);

    const config: AxiosRequestConfig = {
      method: 'get',
      url: `${BASE_URL}/screenshot/region?${params.toString()}`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
    };
    const response = await this.makeRequest(config, 'capture regional screenshot');
    const base64Data = response.data.data.includes(',') ? response.data.data.split(',')[1] : response.data.data;
    return {
      content: [
        {
          type: "image",
          data: base64Data,
          mimeType: `image/${response.data.format}`,
        },
        {
          type: "text",
          text: `Regional screenshot captured. Cursor position: (${response.data.cursor_position.x}, ${response.data.cursor_position.y})`,
        },
      ],
    };
  }

  private async getScreenSize() {
    if (!this.machineId) {
      throw new McpError(
        ErrorCode.InternalError,
        "Machine ID is not set. Please call start() first."
      );
    }
    const config: AxiosRequestConfig = {
      method: 'get',
      url: `${BASE_URL}/system/info?machineId=${encodeURIComponent(this.machineId)}`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
    };
    const response = await this.makeRequest(config, 'get screen size');
    const screenResolution = response.data.screen_resolution;
    return {
      content: [
        {
          type: "text",
          text: `Screen size: ${screenResolution.width}x${screenResolution.height}`,
        },
      ],
    };
  }
}
