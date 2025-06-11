import axios, { AxiosRequestConfig } from "axios";

const BASE_URL = "https://api.nexus.sepalai.com/openapi/eval-machines"

export interface GoalStateReachedResponse {
  filePath: string;
  goalReached: boolean;
  diffString: string;
  diffLength: number | null;
  note: string;
}

export interface MachineCatalog {
  id: string;
  taskShortName: string;
  machineType: string;
  taskDescription: string;
}

export class SepalUtilities {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async listMachineCatalogs(): Promise<MachineCatalog[]> {
    const config: AxiosRequestConfig = {
      method: 'get',
      url: `${BASE_URL}/catalog`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
    };
    const response = await this.makeRequest(config, 'list machine catalogs');
    return response.data;
  }

  async checkGoalStateReached(machineId: string): Promise<GoalStateReachedResponse[]> {
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/goal-state-reached`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: machineId,
      }),
    };
    const response = await this.makeRequest(config, 'check goal state reached');
    return response.data;
  }

  async shutdownMachine(machineId: string): Promise<{ status: string }> {
    const config: AxiosRequestConfig = {
      method: 'post',
      url: `${BASE_URL}/shutdown`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      data: JSON.stringify({
        machineId: machineId,
      }),
    };
    const response = await this.makeRequest(config, 'shutdown machine');
    return response.data;
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
      throw new Error(`Failed to ${operation}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
}
