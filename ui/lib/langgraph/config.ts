/**
 * 版权所有 (c) 2023-2026 北京慧测信息技术有限公司(但问智能) 保留所有权利。
 * 
 * 本代码版权归北京慧测信息技术有限公司(但问智能)所有，仅用于学习交流目的，未经公司商业授权，
 * 不得用于任何商业用途，包括但不限于商业环境部署、售卖或以任何形式进行商业获利。违者必究。
 * 
 * 授权商业应用请联系微信：huice666
 */

import { getLangGraphUrl } from "./utils";

export interface StandaloneConfig {
  deploymentUrl: string;
  assistantId: string;
  langsmithApiKey?: string;
}
// NOTE  MC8yOmFIVnBZMlhsdktEbHVwNDZTMnBFYlE9PToyZjlmNTcxMQ==

const CONFIG_KEY = "deep-agent-config";
// eslint-disable  MS8yOmFIVnBZMlhsdktEbHVwNDZTMnBFYlE9PToyZjlmNTcxMQ==

export function getConfig(): StandaloneConfig | null {
  if (typeof window === "undefined") return null;

  const stored = localStorage.getItem(CONFIG_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      // fall through to env vars
    }
  }

  // Fall back to environment variables or auto-detect from current host
  const deploymentUrl = getLangGraphUrl();
  const assistantId = process.env.NEXT_PUBLIC_TESTCASE_GENERATOR_ASSISTANT_ID;

  if (assistantId) {
    return {
      deploymentUrl,
      assistantId,
      langsmithApiKey: process.env.NEXT_PUBLIC_LANGSMITH_API_KEY,
    };
  }

  return null;
}

export function saveConfig(config: StandaloneConfig): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
}
