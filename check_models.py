from openai import OpenAI

# ⚠️ 请在这里填入你刚才在 Google 申请的 API Key
GEMINI_API_KEY = "YOUR_API_KEY"

def main():
    print("🔍 正在连接 Google 服务器，获取您账号可用的模型列表...\n")
    try:
        client = OpenAI(
            api_key=GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        models = client.models.list()
        
        print("✅ 您的 API Key 支持以下模型代号 (请从中挑选一个填入 main.py 中):")
        print("-" * 50)
        for model in models:
            # 过滤掉一些不能用来做文字翻译的模型，只保留能用来聊天的模型
            if "vision" not in model.id and "embedding" not in model.id and "aqa" not in model.id:
                print(f"👉 {model.id}")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ 获取失败，请检查网络代理是否开启全局模式，或 Key 是否正确。\n错误信息: {e}")

if __name__ == "__main__":
    main()