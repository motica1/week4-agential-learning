import os
from .base_agent import Agent
import chainlit as cl

IMPLEMENTATION_PROMPT = """
You are an expert web developer tasked with implementing the plan for a web page. Your role is to create and update HTML and CSS files based on the current milestone in the plan. Follow these steps:

1. Review the current plan in the 'plan.md' file.
2. Identify the next uncompleted milestone (marked with '- [ ]').
3. Implement or update the 'index.html' and 'style.css' files to complete ONLY this single milestone.
4. Mark the completed milestone in 'plan.md' by changing '- [ ]' to '- [x]'.
5. Provide a summary of the changes made.

Guidelines:
- Focus on implementing one milestone at a time to ensure accuracy and easier debugging.
- Use semantic HTML5 elements where appropriate.
- Write clean, well-commented CSS.
- Ensure your code is responsive and follows best practices.
- If you need to use placeholder images, use 'https://via.placeholder.com/300' with appropriate sizes.

After implementing the changes:
1. Use the 'updateArtifact' function to update 'index.html', 'style.css', and 'plan.md'.
2. Provide a brief explanation of the changes made and any design decisions.

If given feedback on a previous implementation:
1. Carefully review the feedback.
2. Make the necessary adjustments to the HTML and CSS files to address the feedback.
3. Update the relevant files using the 'updateArtifact' function.
4. Summarize the changes made in response to the feedback.

Remember, you are only implementing one milestone at a time or addressing specific feedback. Do not implement future milestones until instructed.
"""

class ImplementationAgent(Agent):
    def __init__(self, client, gen_kwargs=None):
        super().__init__("Implementation Agent", client, IMPLEMENTATION_PROMPT, gen_kwargs)

    async def execute(self, message_history):
        """
        Executes the agent's main functionality.

        This method implements the specific behavior of the ImplementationAgent
        without calling the base Agent's execute method. It follows these steps:
        1. Reviews the current plan in 'plan.md'
        2. Identifies the next uncompleted milestone
        3. Implements or updates 'index.html' and 'style.css' for that milestone
        4. Marks the completed milestone in 'plan.md'
        5. Provides a summary of changes
        
        If given feedback, it adjusts the implementation accordingly.

        Returns:
            str: A summary of the changes made or actions taken
        """
        # Copy the message history to avoid modifying the original
        copied_message_history = message_history.copy()

        # Insert the agent's prompt at the beginning if not already present
        if not copied_message_history or copied_message_history[0]["role"] != "system":
            copied_message_history.insert(0, {"role": "system", "content": self._build_system_prompt()})
        else:
            copied_message_history[0] = {"role": "system", "content": self._build_system_prompt()}

        # Create a response message
        response_message = cl.Message(content="")
        await response_message.send()

        # Generate the completion
        stream = await self.client.chat.completions.create(
            messages=copied_message_history,
            stream=True,
            tools=self.tools,
            tool_choice="auto",
            **self.gen_kwargs
        )

        # Process the stream
        function_name = ""
        arguments = ""
        async for part in stream:
            if part.choices[0].delta.tool_calls:
                tool_call = part.choices[0].delta.tool_calls[0]
                function_name += tool_call.function.name or ""
                arguments += tool_call.function.arguments or ""
            
            if token := part.choices[0].delta.content or "":
                await response_message.stream_token(token)

        # Handle function calls
        if function_name:
            if function_name == "updateArtifact":
                import json
                
                arguments_dict = json.loads(arguments)
                filename = arguments_dict.get("filename")
                contents = arguments_dict.get("contents")
                
                if filename and contents:
                    os.makedirs("artifacts", exist_ok=True)
                    with open(os.path.join("artifacts", filename), "w") as file:
                        file.write(contents)
                    
                    # Add a message to the message history
                    copied_message_history.append({
                        "role": "system",
                        "content": f"The artifact '{filename}' was updated."
                    })

                    # Generate a response about the update
                    update_stream = await self.client.chat.completions.create(
                        messages=copied_message_history,
                        stream=True,
                        **self.gen_kwargs
                    )
                    async for part in update_stream:
                        if token := part.choices[0].delta.content or "":
                            await response_message.stream_token(token)
            elif function_name == "callAgent":
                import json
                
                arguments_dict = json.loads(arguments)
                agent = arguments_dict.get("agent")
                if agent == "implementation":
                    # Recursive call to self
                    implementation_result = await self.execute(copied_message_history)
                    await response_message.stream_token(implementation_result)
        else:
            print("No tool call")

        await response_message.update()

        return response_message.content
        return await super().execute(message_history)

    def _build_system_prompt(self):
        # Custom system prompt building if needed
        return super()._build_system_prompt()

# Additional methods specific to ImplementationAgent can be added here
