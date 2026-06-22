import json
import os
import traceback
from portkey_ai import Portkey

portkey = Portkey(
    api_key=os.getenv("PORTKEY_API_KEY"),
    base_url="https://aigateway.jhuapl.edu/v1"
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
]

def run_agentic_workflow(user_input: str, tool_executor, history=None):
    if history is None or len(history) == 0:
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are a precise HR Assistant. Use the provided tools to validate, manage, and update employee records. "
                    "CRITICAL LOGIC: Before updating, you MUST call fetch_employee. "
                    "Compare the fetched record with the provided data. "
                    "If the data is identical, DO NOT call update_employee. Instead, tell the user that the record is already up to date. "
                    "Only use update_employee if at least one field is different. "
                    "Always provide a friendly, natural language response to the user after using your tools."
                )
            },
            {"role": "user", "content": user_input}
        ]
    else:
        messages = [
            {
                "role": "system", 
                "content": "You are a precise HR Assistant. Use the provided tools to validate, manage, and update employee records."
            }
        ] + history + [{"role": "user", "content": user_input}]

    for _ in range(5):
        try:
            response = portkey.chat.completions.create(
                model="@azure-eagle_cui/o3-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
        except Exception as e:
            traceback.print_exc()
            raise e 

        response_message = response.choices[0].message
        
        if response_message.content and not response_message.tool_calls:
            messages.append({"role": "assistant", "content": response_message.content})
            return response_message.content, messages

        if response_message.tool_calls:
            messages.append({
                "role": "assistant", 
                "content": None, 
                "tool_calls": response_message.tool_calls
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