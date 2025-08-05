from openai import OpenAI
import os

# LLM Client
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "exit":
        print(" Exiting.")
        break
    try:
        # Prepare prompt
        prompt = f"""Battery Status: {user_input}
        You are a bitdecoder for a battery status hex value. 
        Analyse this result {result} and give a conclusion about the battery status.
        """
        
            # Call LLM
        response = client.chat.completions.create(
        model="deepseek/deepseek-r1-0528-qwen3-8b:free",
        messages=[
            {"role": "system", "content": "You are an expert code explainer. Answer clearly."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
        )

        reply = response.choices[0].message.content.strip()
        print(f"🧠 Explanation:\n{reply}\n")

    except Exception as e:
        print("❌ Error:", str(e))
