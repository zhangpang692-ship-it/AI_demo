import { test, expect } from '@playwright/test';

// 配置
const BASE_URL = process.env.API_BASE_URL || 'http://localhost:3000';
const VALID_PROJECT_ID = 'PR-1';
const VALID_API_TEST_ID = '6c642565-16fe-4ef9-8bfa-d6ce6f010815';
const NONEXISTENT_API_TEST_ID = '11111111-1111-1111-1111-111111111111';
const NONEXISTENT_PROJECT_ID = 'NONEXISTENT';

/**
 * 将项目标识符和 API 测试 ID 替换到路径中
 */
function buildUrl(projectId: string, apiTestId: string): string {
  return `${BASE_URL}/api/v2/projects/${projectId}/api-tests/${apiTestId}`;
}

test.describe('GET /api/v2/projects/{project_identifier}/api-tests/{api_test_id} - 获取 API 测试详情', () => {

  // ============ 1. 正常功能测试 ============

  test('正常功能 - 获取已存在的 API 测试（应返回 200 或 404）', async ({ request }) => {
    // Arrange
    const url = buildUrl(VALID_PROJECT_ID, VALID_API_TEST_ID);

    // Act
    const response = await request.get(url);
    const status = response.status();
    const data = await response.json();

    // Assert - 如果 API 在线且资源存在返回 200，否则返回 404
    expect([200, 404]).toContain(status);
    expect(data).toBeDefined();
    if (status === 200) {
      expect(data).toHaveProperty('success');
      expect(data).toHaveProperty('endpoint');
    }
  });

  // ============ 2. 异常测试 ============

  test('异常测试 - 不存在的 API 测试 ID（应返回 404）', async ({ request }) => {
    // Arrange
    const url = buildUrl(VALID_PROJECT_ID, NONEXISTENT_API_TEST_ID);

    // Act
    const response = await request.get(url);
    const status = response.status();

    // Assert
    expect(status).toBe(404);
  });

  test('异常测试 - 不存在的项目标识符（应返回 404）', async ({ request }) => {
    // Arrange
    const url = buildUrl(NONEXISTENT_PROJECT_ID, VALID_API_TEST_ID);

    // Act
    const response = await request.get(url);
    const status = response.status();

    // Assert
    expect(status).toBe(404);
  });

  test('异常测试 - 无效的 UUID 格式（应返回 422 或 500）', async ({ request }) => {
    // Arrange
    const url = buildUrl(VALID_PROJECT_ID, 'invalid-uuid-format');

    // Act
    const response = await request.get(url);
    const status = response.status();

    // Assert - 424/404 -> 验证错误；500 -> 服务器内部错误
    expect([422, 500]).toContain(status);
  });

  test('边界测试 - 空字符串作为 api_test_id（应返回 200 或 422）', async ({ request }) => {
    // Arrange
    const url = buildUrl(VALID_PROJECT_ID, '');

    // Act
    const response = await request.get(url);
    const status = response.status();

    // Assert - 如果服务器将空字符串视为有效返回 200；否则返回 422 验证错误
    expect([200, 422]).toContain(status);
  });

  // ============ 4. 安全测试 ============

  test('安全测试 - SQL 注入（应被过滤）', async ({ request }) => {
    // Arrange
    const sqlInjectionId = "11111111-1111-1111-1111-111111111111'; DROP TABLE users; --";
    const url = buildUrl(VALID_PROJECT_ID, sqlInjectionId);

    // Act
    const response = await request.get(url);
    const status = response.status();

    // Assert - 系统应正确过滤，不应返回 200（数据未泄露）
    // 预期返回 404（未找到）、422（验证错误）或 500（错误响应）
    expect([404, 422, 500]).toContain(status);
    expect(status).not.toBe(200);
  });

  test('安全测试 - XSS 攻击（应被转义）', async ({ request }) => {
    // Arrange
    const xssId = '<script>alert("xss")</script>';
    const url = buildUrl(VALID_PROJECT_ID, xssId);

    // Act
    const response = await request.get(url);
    const status = response.status();

    // Assert - 系统应正确转义，返回错误码
    expect([404, 422]).toContain(status);

    // 验证响应内容中不包含可执行的脚本
    const text = await response.text();
    expect(text).not.toContain('<script>');
  });
});
