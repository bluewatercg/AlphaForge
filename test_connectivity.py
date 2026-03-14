"""test_connectivity.py - 测试 AKShare 数据源和 LLM API 连通性"""

print("=" * 50)
print("ATLAS-A 连通性测试")
print("=" * 50)

# === 测试1: AKShare 涨停池 ===
print("\n[1/5] 涨停池 (datacenter-web.eastmoney.com)...")
try:
    import akshare as ak
    df = ak.stock_zt_pool_em(date="20260313")
    print(f"  ✅ 成功: {len(df)} 条")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# === 测试2: 指数行情 ===
print("\n[2/5] 指数行情 (push2.eastmoney.com)...")
try:
    df = ak.stock_zh_index_spot_em()
    print(f"  ✅ 成功: {len(df)} 条")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# === 测试3: 全市场快照 ===
print("\n[3/5] 全市场快照 (push2.eastmoney.com)...")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"  ✅ 成功: {len(df)} 条")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# === 测试4: 行业板块 ===
print("\n[4/5] 行业板块...")
try:
    df = ak.stock_board_industry_name_em()
    print(f"  ✅ 成功: {len(df)} 条")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# === 测试5: LLM API ===
print("\n[5/5] LLM API (百炼)...")
try:
    from dotenv import load_dotenv
    import os
    load_dotenv()

    # 兼容带引号的 .env key
    def get(k):
        return (os.getenv(k) or os.getenv(f'"{k}"') or "").strip('"').strip("'")

    from openai import OpenAI
    client = OpenAI(
        api_key=get("OPENAI_API_KEY"),
        base_url=get("OPENAI_BASE_URL") or get("BASE_URL"),
    )
    resp = client.chat.completions.create(
        model=get("LLM_MODEL") or "glm-5",
        max_tokens=50,
        messages=[{"role": "user", "content": "用一句话解释什么是涨停板"}],
    )
    print(f"  ✅ 成功: {resp.choices[0].message.content}")
except Exception as e:
    print(f"  ❌ 失败: {e}")

print("\n" + "=" * 50)
print("测试完成！5个全绿就可以跑 python main.py --date 20260313")
