import google.generativeai as genai
import os

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))


def get_llm_response(messages, system_prompt=None):
    model = genai.GenerativeModel(
        model_name=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
        system_instruction=system_prompt,
    )
    history = []
    for m in messages[:-1]:
        history.append({
            'role': m['role'],
            'parts': [m['content']],
        })
    chat = model.start_chat(history=history)
    response = chat.send_message(messages[-1]['content'])
    return response.text


def get_structured_output(text, instructions):
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"{instructions}\n\n{text}"
    response = model.generate_content(prompt)
    return response.text
