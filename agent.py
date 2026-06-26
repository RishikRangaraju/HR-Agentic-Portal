import json
import os
import traceback
from portkey_ai import Portkey

portkey = Portkey(
    api_key=os.getenv("PORTKEY_API_KEY"),
    base_url=os.getenv("PORTKEY_BASE_URL"),
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_employee",
            "description": "Look up an employee's record by their employee ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "The unique ID of the employee (e.g., E001)"},
                },
                "required": ["employee_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_employee",
            "description": "Create a new employee record in the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "email": {"type": "string"},
                    "date_of_birth": {"type": "string", "description": "YYYY-MM-DD"},
                    "hire_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "department": {"type": "string", "enum": ["ENGINEERING", "HR", "SALES", "MARKETING"]},
                    "manager_id": {"type": "string"},
                    "employment_type": {"type": "string", "enum": ["FULL_TIME", "PART_TIME", "CONTRACTOR"]},
                },
                "required": ["employee_id", "first_name", "last_name", "email", "date_of_birth", "hire_date", "department"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_employee",
            "description": "Update specific fields of an existing employee record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "ID of the employee to update"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "email": {"type": "string"},
                    "department": {"type": "string", "enum": ["ENGINEERING", "HR", "SALES", "MARKETING"]},
                    "manager_id": {"type": "string"},
                    "employment_type": {"type": "string", "enum": ["FULL_TIME", "PART_TIME", "CONTRACTOR"]},
                },
                "required": ["employee_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_employee",
            "description": "Permanently delete an employee record from the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "ID of the employee to delete"},
                },
                "required": ["employee_id"],
            },
        },  
    },
    {
        "type": "function",
        "function": {
            "name": "search_employees",
            "description": "Search for employees by name if the ID is unknown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_query": {"type": "string", "description": "The name or partial name to search for"},
                },
                "required": ["name_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_employees",
            "description": "Get the total number of employees currently in the system.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_employees",
            "description": "Retrieve a list of all employees in the system, including their names and IDs.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get the current date to be used as a reference for all age and tenure calculations.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {


        "type": "function",
        "function": {
            "name": "get_department_stats",
            "description": "Get a count of how many employees are in each department.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_employment_type_stats",
            "description": "Get a count of employees by their employment type (e.g., FULL_TIME, CONTRACTOR).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_age_statistics",
            "description": "Get high-level age statistics including the oldest, youngest, and average age of all employees.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

def run_agentic_workflow(user_input: str, tool_executor, history=None):
    system_prompt = (
    "You are a precise and professional HR Assistant. "
    "Use tools to manage records. Before updating, you MUST call fetch_employee. "
    "If a tool requires missing info, ask the user. "
    
    "KNOWLEDGE BOUNDARY: You are an internal HR Assistant. For any questions regarding "
    "employee records, company policies, or specific data, rely EXCLUSIVELY on your tools. "
    "If the tools do not provide the answer, state that you do not have access to that "
    "information. Do not use your general training data to fill in gaps in company records. "
    
    "WORLD KNOWLEDGE: If a user asks a general world-knowledge question (e.g., 'Who is the "
    "oldest person in the world?'), explicitly state that you do not have access to the "
    "live internet and cannot provide real-time global information."
    
    "STRICT EXECUTION RULE: Do not 'pre-announce' your actions. Never say 'Let me check,' "
    "'I will look that up,' or 'I am going to fetch the records.' Instead, call the required "
    "tool immediately. Only provide a text response AFTER you have received the tool results. "
    
    "MULTI-STEP TASKS: If a request requires multiple steps (e.g., finding an ID then fetching a record), "
    "execute the first tool immediately. Do not tell the user you are starting the process; "
    "just start it. "
    
    "NO CODE OUTPUT: You are an HR Assistant, not a programmer. NEVER output Python code, "
    "scripts, or formulas. Perform all calculations (like age or tenure) internally using "
    "the data from tools and provide the result as a natural language sentence. "
    
    "AGE CALCULATIONS: To calculate age, use the `get_current_date` tool for the reference year "
    "and the `date_of_birth` from the employee record. Subtract the birth year from the "
    "current year. "
    
    "FINAL ANSWER: Your final response should only be generated once you have all the necessary "
    "data from your tools to fully answer the user's request."
    
    "\n\n"
    "Do not explain your internal reasoning. Provide natural, concise responses."
)

    if history is None or len(history) == 0:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    else:
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_input}]

    for _ in range(5):
        try:
            response = portkey.openai_client.chat.completions.create(
                model="@opal/meta-llama/Llama-3.3-70B-Instruct",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                extra_headers={
                    "x-portkey-config": os.getenv("PORTKEY_CONFIG_ID"),
                    "x-portkey-metadata": json.dumps({
                        "user_id": "demo_user",
                        "project_id": os.getenv("PORTKEY_CONFIG_ID")
                    })
                }
            )
        except Exception as e:
            traceback.print_exc()
            raise e 

        response_message = response.choices[0].message
        
        if response_message.content and not response_message.tool_calls:
            messages.append({"role": "assistant", "content": response_message.content})
            return response_message.content, messages

        if response_message.tool_calls:
            tool_calls_as_dicts = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in response_message.tool_calls
            ]

            messages.append({
                "role": "assistant", 
                "content": "", 
                "tool_calls": tool_calls_as_dicts
            })
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                result = tool_executor(function_name, args)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(result),
                })

    return "I'm sorry, I couldn't complete the task.", messages