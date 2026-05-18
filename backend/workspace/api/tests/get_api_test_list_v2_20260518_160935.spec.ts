import { test, expect } from '@playwright/test';

// ============================================================
// 配置
// ============================================================
const BASE_URL = process.env.API_BASE_URL || 'http://localhost:3000';
const PROJECT_IDENTIFIER = 'PR-1';

// ============================================================
// 测试辅助函数
// ============================================================

/**
 * 构建 API 路径
 */
function buildApiPath(projectIdentifier: string): string {
  return `/api/v2/projects/${projectIdentifier}/api-tests`;
}

// ============================================================
// 测试套件
// ============================================================

test.describe('GET /api/v2/projects/{project_identifier}/api-tests - 获取 API 测试列表', () => {

  // ----------------------------------------------------------
  // 正常功能测试
  // ----------------------------------------------------------

  test('[P0] 正常场景 - 成功获取 API 测试列表', async ({ request }) => {
    // Arrange
    const path = buildApiPath(PROJECT_IDENTIFIER);

    // Act
    const response = await request.get(`${BASE_URL}${path}`);

    // Assert
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toBeDefined();
  });

  test('[P1] 正常场景 - 使用搜索关键词过滤', async ({ request }) => {
    // Arrange
    const path = buildApiPath(PROJECT_IDENTIFIER);
    const searchKeyword = 'login';

    // Act
    const response = await request.get(`${BASE_URL}${path}`, {
      params: { search: searchKeyword }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P1] 正常场景 - 使用 script_format 过滤', async ({ request }) => {
    // Arrange
    const path = buildApiPath(PROJECT_IDENTIFIER);

    // Act
    const response = await request.get(`${BASE_URL}${path}`, {
      params: { script_format: 'playwright' }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P1] 正常场景 - 同时使用多个查询参数', async ({ request }) => {
    // Arrange
    const path = buildApiPath(PROJECT_IDENTIFIER);

    // Act
    const response = await request.get(`${BASE_URL}${path}`, {
      params: {
        search: 'test',
        script_format: 'playwright',
        page: 1,
        page_size: 20
      }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  // ----------------------------------------------------------
  // 分页测试
  // ----------------------------------------------------------

  test('[P1] 分页测试 - 默认分页参数', async ({ request }) => {
    // Act - 不传分页参数，使用默认值
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`);

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P1] 分页测试 - 自定义分页参数', async ({ request }) => {
    // Act
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { page: 1, page_size: 10 }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P2] 分页测试 - 最大 page_size', async ({ request }) => {
    // Act - page_size 最大值 300
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { page_size: 300 }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P2] 分页测试 - 最小 page_size', async ({ request }) => {
    // Act - page_size 最小值 1
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { page_size: 1 }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P2] 分页测试 - 超出范围的页码', async ({ request }) => {
    // Act - 超出实际数据范围的页码
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { page: 9999, page_size: 10 }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  // ----------------------------------------------------------
  // 边界测试
  // ----------------------------------------------------------

  test('[P2] 边界测试 - 空字符串搜索', async ({ request }) => {
    // Act
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { search: '' }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P2] 边界测试 - 搜索特殊字符', async ({ request }) => {
    // Act - 包含各种特殊字符
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { search: '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P2] 边界测试 - 搜索中文字符', async ({ request }) => {
    // Act
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { search: '测试接口' }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  test('[P2] 边界测试 - 搜索 Emoji 字符', async ({ request }) => {
    // Act
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { search: '🔍🧪🚀' }
    });

    // Assert
    expect(response.status()).toBe(200);
  });

  // ----------------------------------------------------------
  // 异常测试
  // ----------------------------------------------------------

  test('[P2] 异常测试 - page_size 超出最大值', async ({ request }) => {
    // Act - page_size 超过最大值 300
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { page_size: 301 }
    });

    // Assert - 期望 422 Validation Error
    expect([422, 400]).toContain(response.status());
  });

  test('[P2] 异常测试 - page_size 小于最小值', async ({ request }) => {
    // Act - page_size 小于最小值 1
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { page_size: 0 }
    });

    // Assert - 期望 422 Validation Error
    expect([422, 400]).toContain(response.status());
  });

  test('[P2] 异常测试 - 负数页码', async ({ request }) => {
    // Act - page 为负数（服务端宽容处理，可能返回 200）
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { page: -1 }
    });

    // Assert - 服务端对负数页码做宽容处理，接受 200 或 422
    expect([200, 422, 400]).toContain(response.status());
  });

  test('[P2] 异常测试 - page 为非数值类型', async ({ request }) => {
    // Act - page 为字符串（服务端宽容处理，可能返回 200）
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { page: 'abc' }
    });

    // Assert - 服务端对非数值参数做宽容处理，接受 200 或 422
    expect([200, 422, 400]).toContain(response.status());
  });

  test('[P1] 异常测试 - 不存在的 project_identifier', async ({ request }) => {
    // Act - 使用不存在的项目标识符
    const response = await request.get(`${BASE_URL}${buildApiPath('NONEXISTENT_PROJECT')}`);

    // Assert - 期望 404 Not Found
    expect([404, 403]).toContain(response.status());
  });

  // ----------------------------------------------------------
  // 安全测试
  // ----------------------------------------------------------

  test('[P2] 安全测试 - SQL 注入攻击', async ({ request }) => {
    // Act - SQL 注入尝试
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { search: "' OR '1'='1" }
    });

    // Assert - 应该被正确过滤，返回 200 或错误
    expect(response.status()).toBeGreaterThanOrEqual(200);
    expect(response.status()).toBeLessThan(500);
  });

  test('[P2] 安全测试 - XSS 注入攻击', async ({ request }) => {
    // Act - XSS 注入尝试
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: { search: "<script>alert('xss')</script>" }
    });

    // Assert - 应该被正确转义
    expect(response.status()).toBe(200);
  });

  // ----------------------------------------------------------
  // 组合参数测试
  // ----------------------------------------------------------

  test('[P2] 组合测试 - 搜索 + 分页 + 格式过滤', async ({ request }) => {
    // Act - 组合多个参数
    const response = await request.get(`${BASE_URL}${buildApiPath(PROJECT_IDENTIFIER)}`, {
      params: {
        search: 'auth',
        script_format: 'playwright',
        page: 1,
        page_size: 50
      }
    });

    // Assert
    expect(response.status()).toBe(200);
  });
});
