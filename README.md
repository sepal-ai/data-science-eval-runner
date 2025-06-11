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
