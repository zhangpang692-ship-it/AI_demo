import { test, expect } from '@playwright/test';

// 配置
const BASE_URL = process.env.API_BASE_URL || 'https://api.example.com';
const AUTH_TOKEN = process.env.AUTH_TOKEN || '';

// 默认认证请求头
const getAuthHeaders = (token?: string) => ({
  'Authorization': `Bearer ${token || AUTH_TOKEN}`,
  'Content-Type': 'application/json',
});

test.describe('DELETE /api/v2/projects/{project_identifier}/api-tests/{api_test_id} - 删除 API 测试', () => {

  // ==================== 正常功能测试 ====================

  test('1.1 成功删除存在的 API 测试 - 应返回 200', async ({ request }) => {
    // Arrange
    const projectIdentifier = 'PR-1';
    const apiTestId = 'valid-test-id';

    // Act
    const response = await request.delete(
      `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${apiTestId}`,
      {
        headers: getAuthHeaders(),
      }
    );

    // Assert
    expect(response.status()).toBe(200);
    const data = await response.json();
    // 验证 SuccessResponse schema 结构
    expect(data).toBeDefined();
    // 预期响应应包含成功标志
    expect(typeof data).toBe('object');
  });

  // ==================== 异常测试 ====================

  test('2.1 删除不存在的 API 测试 - 应返回 404 或 422', async ({ request }) => {
    // Arrange
    const projectIdentifier = 'PR-1';
    const nonExistentTestId = 'non-existent-test-id';

    // Act
    const response = await request.delete(
      `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${nonExistentTestId}`,
      {
        headers: getAuthHeaders(),
      }
    );

    // Assert - 资源不存在，应该返回错误状态码
    expect([404, 422]).toContain(response.status());
    const error = await response.json().catch(() => ({}));
    expect(error).toBeDefined();
  });

  test('2.2 无效的 project_identifier - 应返回 422', async ({ request }) => {
    // Arrange
    const invalidProjectId = 'non-existent-project';
    const apiTestId = 'test-id-123';

    // Act
    const response = await request.delete(
      `${BASE_URL}/api/v2/projects/${invalidProjectId}/api-tests/${apiTestId}`,
      {
        headers: getAuthHeaders(),
      }
    );

    // Assert - 无效的项目标识符应返回验证错误
    expect(response.status()).toBe(422);
    const error = await response.json().catch(() => ({}));
    expect(error).toBeDefined();
  });

  test('2.3 空字符串 api_test_id - 应返回 422', async ({ request }) => {
    // Arrange
    const projectIdentifier = 'PR-1';
    const emptyTestId = '';

    // Act
    const response = await request.delete(
      `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${emptyTestId}`,
      {
        headers: getAuthHeaders(),
      }
    );

    // Assert - 空参数应返回验证错误
    expect(response.status()).toBe(422);
    const error = await response.json().catch(() => ({}));
    expect(error).toBeDefined();
  });

  // ==================== 边界测试 ====================

  test('3.1 重复删除同一 API 测试 - 第一次应成功，第二次应返回错误', async ({ request }) => {
    // Arrange
    const projectIdentifier = 'PR-1';
    const apiTestId = 'test-to-delete-twice';

    // Act - 第一次删除
    const firstResponse = await request.delete(
      `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${apiTestId}`,
      {
        headers: getAuthHeaders(),
      }
    );

    // Assert - 第一次删除应成功
    expect(firstResponse.status()).toBe(200);

    // Act - 第二次删除（资源已不存在）
    const secondResponse = await request.delete(
      `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${apiTestId}`,
      {
        headers: getAuthHeaders(),
      }
    );

    // Assert - 第二次删除应返回资源不存在的错误
    expect([404, 422]).toContain(secondResponse.status());
  });

  // ==================== 安全测试 ====================

  test('4.1 无认证 Token 调用删除接口 - 应返回 401', async ({ request }) => {
    // Arrange
    const projectIdentifier = 'PR-1';
    const apiTestId = 'test-id-123';

    // Act - 不携带 Authorization 头
    const response = await request.delete(
      `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${apiTestId}`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    // Assert - 应返回未授权
    expect(response.status()).toBe(401);
  });

  test('4.2 无效/伪造的 Token 调用删除接口 - 应返回 401 或 403', async ({ request }) => {
    // Arrange
    const projectIdentifier = 'PR-1';
    const apiTestId = 'test-id-123';

    // Act - 携带无效的 Token
    const response = await request.delete(
      `${BASE_URL}/api/v2/projects/${projectIdentifier}/api-tests/${apiTestId}`,
      {
        headers: {
          'Authorization': 'Bearer invalid-or-expired-token',
          'Content-Type': 'application/json',
        },
      }
    );

    // Assert - 应返回无权限
    expect([401, 403]).toContain(response.status());
  });
});
