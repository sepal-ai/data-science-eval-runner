# Sepal AI Claude Agent Evaluation

This is an example repo on how to use Sepal AI's computer-use eval framework. 

## Features

- **Claude Integration**: Uses Anthropic's Claude models with advanced reasoning capabilities
- **Computer Use**: MCP (Model Context Protocol) integration for computer interaction using Sepal AI's APIs
- **Flexible Configuration**: Configurable model, machine type, and execution parameters
- **Real-time CLI**: CLI for running agent eval locally

## Prerequisites

- **Node.js**
- **npm**
- **API Keys**: 
  - Anthropic API key (for Claude access)
  - Sepal AI API key (for MCP computer-use capabilities)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sepal-ai/agent-eval-claude.git
   cd agent-eval-claude
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   Create a `.env.local` file in the project root:
   ```bash
   touch .env.local
   ```

4. **Configure your API keys**:
   Add the following to your `.env.local` file:
   ```env
   ANTHROPIC_API_KEY=<your-anthropic-key-here>
   SEPAL_AI_API_KEY=<your-sepal-key-here>
   ```

## Usage

### CLI
Run the CLI to test out the agent:
```bash
npm run run-agent-eval
```

## Configuration

The agent accepts various configuration parameters:

### Supported Models
- `claude-opus-4-20250514` (supports thinking)
- `claude-sonnet-4-20250514` (supports thinking)  
- `claude-3-7-sonnet-20250219` (supports thinking)
- Other Claude models (without thinking capabilities)

### Machine Types
Configure the MCP server machine type based on your requirements:
- libreoffice (open-source Excel-alternative)
- appflowy (open-source Notion-alternative)
- firefox

### Parameters
- **model**: Claude model to use
- **machineType**: MCP server machine configuration
- **taskPrompt**: The task description for the agent
- **systemPrompt**: System-level instructions
- **thinking**: Enable thinking for supported models
- **maxIterations**: Maximum conversation iterations
- **maxTokens**: Maximum tokens per request

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude API    │    │   Claude Agent   │    │   MCP Server    │
│                 │◄──►│                  │◄──►│  (Computer Use) │
│ - Text Gen      │    │ - Conversation   │    │ - Screenshots   │
│ - Tool Use      │    │ - Tool Execution │    │ - Mouse/Keys    │
│ - Thinking      │    │ - Event Relay    │    │ - Applications  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

# Sepal Computer Use API Documentation

This section provides comprehensive documentation for the Evaluation Machines and Agent Evaluation Run APIs from Sepal AI.

## Table of Contents

## Overview

The API provides a comprehensive platform for:
- Creating and managing virtual evaluation machines
- Automating UI interactions (mouse, keyboard)
- Running AI agent evaluations
- Verifying goal states
- Capturing screenshots and system information

## Authentication

All endpoints require API token authentication:
- **Header**: `Authorization: Bearer <API_TOKEN>`

## Evaluation Machines API

Base path: `/api/eval-machines`

### Machine Management

#### Machine Catalog
```http
GET /eval-machines/catalog
```

Lists all available machine snapshots/templates.

**Response:**
```json
[
  {
    "id": "snapshot-uuid",
    "taskShortName": "login-flow",
    "taskDescription": "Test user login flow",
    "machineType": "ubuntu-desktop",
    "goalState": [{
      "type": "ods"
      "absoluteFilePath": "...";
      "sheetName": "...";
      "fileContent": "...";
    }]
  }
]
```

#### Create Machine

```http
POST /eval-machines
```

Creates a new evaluation machine from a snapshot.

**Request:**
```json
{
  "alias": "my-test-machine",
  "machine": {
    "snapshotId": "uuid-of-snapshot",
    // OR
    "taskShortName": "task-name"
  },
  "machineExpirationDate": "2024-01-02T00:00:00Z"
}
```

**Response:**
```json
{
  "machineId": "fly-machine-id",
  "appName": "my-test-machine-abc123",
  "vncUrl": "https://vnc.fly.dev/...",
  "machineExpirationDate": "2024-01-02T00:00:00Z"
}
```

#### Get Machine Status
```http
GET /eval-machines/status?machineId=<machine-id>
```

Returns the current status of a specific machine.

**Response:**
```json
{
  "status": "deployed",
  "appName": "machine-name"
}
```

#### Shutdown Machine
```http
POST /eval-machines/shutdown
```

**Request:**
```json
{
  "machineId": "machine-id"
}
```

**Response:**
```json
{
  "status": "success"
}
```

### Goal State Verification

#### Check Goal State
```http
POST /eval-machines/goal-state-reached
```

Verifies if the machine has reached its expected goal state.

**Request:**
```json
{
  "machineId": "machine-id"
}
```

**Response:**
```json
[
  {
    "filePath": "/home/user/status.txt",
    "goalReached": true,
    "diffString": "",
    "diffLength": 0,
    "note": "File matches expected content"
  }
]
```

### UI Automation

#### Mouse Operations

##### Move Mouse
```http
POST /eval-machines/mouse/move
```

**Request:**
```json
{
  "machineId": "machine-id",
  "x": 500,
  "y": 300
}
```

##### Click Mouse
```http
POST /eval-machines/mouse/click
```

**Request:**
```json
{
  "machineId": "machine-id",
  "x": 500,
  "y": 300,
  "button": "left"  // "left", "right", or "middle"
}
```

##### Drag Mouse
```http
POST /eval-machines/mouse/drag
```

**Request:**
```json
{
  "machineId": "machine-id",
  "x": 600,
  "y": 400,
  "duration": 1000  // milliseconds
}
```

#### Keyboard Operations

##### Type Text
```http
POST /eval-machines/keyboard/type
```

**Request:**
```json
{
  "machineId": "machine-id",
  "text": "Hello World"
}
```

##### Press Key
```http
POST /eval-machines/keyboard/press
```

**Request:**
```json
{
  "machineId": "machine-id",
  "key": "Enter",
  "presses": 1
}
```

### Screen Capture

#### Full Screenshot
```http
GET /eval-machines/screenshot?machineId=<machine-id>&crosshairs=true
```

Returns a base64-encoded PNG screenshot.

**Response:**
```json
{
   "status": "success",
   "format": "png",
   "cursor_position": {"x": 500, "y": 500},
   "data": f"data:image/png;base64,<img_str>"
}
```

#### Region Screenshot
```http
GET /eval-machines/screenshot/region?machineId=<machine-id>&x=100&y=100&width=400&height=300
```

Captures a specific region of the screen.

### System Information

#### Get System Info
```http
GET /eval-machines/system/info?machineId=<machine-id>
```

**Response:**
```json
{
   "status": "running",
   "ip_address": "10.0.0.1",
   "hostname": "eval-machine",
   "screen_resolution": {
      "width": 1920,
      "height": 1080
   },
   cursor_position: {
      "x": 960,
      "y": 540,
   },
   "active_window": "Terminal",
   "running_apps": ["Terminal", "Firefox", "VS Code"]
}
```

### File System Operations

#### List Files
```http
GET /eval-machines/fs/list?machineId=<machine-id>&path=/home/user
```

**Response:**
```json
{
  "files": [
    {
      "name": "document.txt",
      "isDirectory": false,
      "size": 1024,
      "modifiedAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### Read File
```http
POST /eval-machines/fs/read-file
```

**Request:**
```json
{
  "machineId": "machine-id",
  "path": "/home/user/document.txt"
}
```

**Response:**
```json
{
  "content": "File content here...",
  "encoding": "utf-8"  // or "base64" for binary files
}
```

## Agent Evaluation Run API

Base path: `/api/agent-eval-runs`

### Start Evaluation Run
```http
POST /agent-eval-runs
```

Starts a new AI agent evaluation on a virtual machine.

**Request:**
```json
{
  "machineSnapshotId": "snapshot-uuid",
  // OR
  "machineSnapshotTaskShortName": "login-flow",
  
  "agentType": "claude",
  "agentConfig": {
    "modelName": "claude-3-sonnet-20240229",
    "modelApiKey": "sk-...",
    "taskPrompt": "Complete the login flow",
    "systemPrompt": "You are a QA tester...",
    "thinking": true,
    "maxIterations": 50,
    "maxTokens": 100000
  }
}
```

**Response:**
```json
{
  "id": "run-uuid"
}
```

### Get Evaluation Run Details
```http
GET /agent-eval-runs/{id}
```

Returns comprehensive details about an evaluation run.

**Response:**
```json
{
  "id": "run-uuid",
  "agentType": "claude",
  "agentConfig": {
    "modelName": "claude-3-sonnet-20240229",
    "thinking": true
  },
  "status": "completed",
  "startedAt": "2024-01-01T00:00:00Z",
  "completedAt": "2024-01-01T00:10:00Z",
  "errorMessage": null,
  "machineSnapshot": {
    "id": "snapshot-uuid",
    "taskShortName": "login-flow",
    "taskDescription": "Test user login flow"
  },
  "machineInstance": {
    "id": "instance-uuid",
    "appName": "eval-machine-abc123",
    "machineId": "fly-machine-id",
    "machineStatus": "running"
  },
  "goalStateCheck": [
    {
      "filePath": "/home/user/status.txt",
      "goalReached": true,
      "diffString": "",
      "diffLength": 0,
      "note": "Goal state achieved"
    }
  ]
}
```

### Get Evaluation Transcript
```http
GET /agent-eval-runs/{id}/transcript
```

Returns the full transcript of agent actions.

**Response:**
```json
[
  {
    "createdAt": "2024-01-01T00:00:00Z",
    "id": "step-uuid",
    "data": {
      "action": "screenshot",
      "result": "screenshot-123.png"
    }
  },
  {
    "createdAt": "2024-01-01T00:00:01Z",
    "id": "step-uuid-2",
    "data": {
      "action": "click",
      "x": 500,
      "y": 300
    }
  }
]
```

### Get Screenshot
```http
GET /agent-eval-runs/{id}/images/{imageFileName}
```

Returns a presigned URL to download screenshots captured during evaluation.

**Response:**
```json
{
  "imageDownloadUrl": "https://storage.example.com/..."
}
```
