import os
from dotenv import load_dotenv
# Add Azure OpenAI package
from openai import AzureOpenAI
load_dotenv()
azure_oai_endpoint = os.getenv("AZURE_OAI_ENDPOINT")
azure_oai_key = os.getenv("AZURE_OAI_KEY")
azure_oai_deployment = os.getenv("AZURE_OAI_DEPLOYMENT")

def send_prompt_to_openai_model(query):
    client = AzureOpenAI(
        azure_endpoint=azure_oai_endpoint,
        api_key=azure_oai_key,
        api_version="2024-02-15-preview"
    )
    model = azure_oai_deployment
    # Provide a basic user message, and use the prompt content as the user message
    system_message = "Based on natural language or function definition or unit test, either code or provide ruby code snippets only and it shouldn't contain ruby keyword and triple quote in response and response should contain one choice"
    user_message = query

    # Format and send the request to the model
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        temperature=0.1,
        max_tokens=8000,
        top_p=1.0,
        n=1,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    print("the query is : {} ".format(query))
    print("the response is: {}".format(response.choices[0].message.content))
    return response.choices[0].message.content

