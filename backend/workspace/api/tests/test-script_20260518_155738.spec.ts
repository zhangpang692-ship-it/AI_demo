import { test, expect } from '@playwright/test';

const BASE_URL = process.env.API_BASE_URL || 'https://api.example.com';
const AUTH_TOKEN = process.env.AUTH_TOKEN || 'test-token';
const PROJECT_ID = process.env.PROJECT_ID || 'PR-1';

const authHeaders = {
  'Authorization': `Bearer ${AUTH_TOKEN}`,
  'Content-Type': 'application/x-www-form-urlencoded'
};

test.describe('创建 API 测试 - POST /api/v2/projects/{project_identifier}/api-tests', () => {

  // ============ 正常功能测试 ============

  test('TC-01: 应成功创建 API 测试并返回 200', async ({ request }) => {
    const formData = new URLSearchParams();
    formData.append('endpoint_id', 'test-endpoint-id');
    formData.append('name', 'Test API Test');
    formData.append('description', 'Created by automated test');

    const response = await request.post(`${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests`, {
      headers: authHeaders,
      data: formData.toString()
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    // 验证成功响应结构
    expect(data).toBeDefined();
  });

  // ============ 参数验证测试 ============

  test('TC-02: 使用无效的 project_identifier 应返回 404/422', async ({ request }) => {
    const formData = new URLSearchParams();
    formData.append('endpoint_id', 'test-endpoint-id');
    formData.append('name', 'Test');

    const response = await request.post(`${BASE_URL}/api/v2/projects/NONEXISTENT/api-tests`, {
      headers: authHeaders,
      data: formData.toString()
    });

    // 预期返回 404（资源不存在）或 422（验证错误）
    expect([404, 422]).toContain(response.status());
  });

  test('TC-03: 空的 project_identifier 应返回 422', async ({ request }) => {
    const formData = new URLSearchParams();
    formData.append('endpoint_id', 'test-endpoint-id');
    formData.append('name', 'Test');

    const response = await request.post(`${BASE_URL}/api/v2/projects//api-tests`, {
      headers: authHeaders,
      data: formData.toString()
    });

    expect(response.status()).toBe(422);
  });

  // ============ 异常测试 ============

  test('TC-04: 缺少请求体应返回 422', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests`, {
      headers: authHeaders
    });

    expect(response.status()).toBe(422);
  });

  test('TC-08: 请求体格式错误应返回 422', async ({ request }) => {
    // 使用 JSON 格式而非 form-urlencoded
    const response = await request.post(`${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests`, {
      headers: {
        'Authorization': `Bearer ${AUTH_TOKEN}`,
        'Content-Type': 'application/json'
      },
      data: JSON.stringify({ endpoint_id: 'test', name: 'Test' })
    });

    expect(response.status()).toBe(422);
  });

  // ============ 安全测试 ============

  test('TC-05: 未授权访问应返回 401', async ({ request }) => {
    const formData = new URLSearchParams();
    formData.append('endpoint_id', 'test-endpoint-id');
    formData.append('name', 'Test');

    const response = await request.post(`${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests`, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      data: formData.toString()
    });

    expect(response.status()).toBe(401);
  });

  test('TC-06: 无效 Token 应返回 401', async ({ request }) => {
    const formData = new URLSearchParams();
    formData.append('endpoint_id', 'test-endpoint-id');
    formData.append('name', 'Test');

    const response = await request.post(`${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests`, {
      headers: {
        'Authorization': 'Bearer invalid-token-12345',
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      data: formData.toString()
    });

    expect(response.status()).toBe(401);
  });
});
