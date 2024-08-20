import threading, time, models, os
from ansio import application_keypad, mouse_input, raw_input
from ansio.input import InputEvent, get_input_event
from agent import Agent, AgentConfig
from python.helpers.print_style import PrintStyle
from python.helpers.files import read_file
from python.helpers import files
import python.helpers.timed_input as timed_input

input_lock = threading.Lock()
os.chdir(files.get_abs_path("./work_dir")) # Change CWD to work_dir

def initialize():
    # Main chat model used by agents (Hugging Face GPT-2 with temperature 0.7)
    chat_llm = models.get_huggingface_chat(model="gpt2", temperature=0.7)
    
    # Use Hugging Face for utility functions (using the same model here for simplicity)
    utility_llm = models.get_huggingface_chat(model="gpt2", temperature=0.7)

    # Use Hugging Face embeddings model for memory
    embedding_llm = models.get_embedding_hf(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Agent configuration
    config = AgentConfig(
        chat_model = chat_llm,
        utility_model = utility_llm,
        embeddings_model = embedding_llm,
        code_exec_docker_enabled = True,
        code_exec_ssh_enabled = True,
    )
    
    # Create the first agent
    agent0 = Agent(number = 0, config = config)

    # Start the chat loop
    chat(agent0)

# Main conversation loop
def chat(agent: Agent):
    # Start the conversation loop  
    while True:
        # Ask user for message
        with input_lock:
            timeout = agent.get_data("timeout")  # How long the agent is willing to wait
            if not timeout:  # If agent wants to wait for user input forever
                PrintStyle(background_color="#6C3483", font_color="white", bold=True, padding=True).print(f"User message ('e' to leave):")
                import readline  # This fixes arrow keys in terminal
                user_input = input("> ")
                PrintStyle(font_color="white", padding=False, log_only=True).print(f"> {user_input}") 
                
            else:  # Otherwise wait for user input with a timeout
                PrintStyle(background_color="#6C3483", font_color="white", bold=True, padding=True).print(f"User message ({timeout}s timeout, 'w' to wait, 'e' to leave):")
                import readline  # This fixes arrow keys in terminal
                user_input = timeout_input("> ", timeout=timeout)

                if not user_input:
                    user_input = read_file("prompts/fw.msg_timeout.md")
                    PrintStyle(font_color="white", padding=False).stream(f"{user_input}")        
                else:
                    user_input = user_input.strip()
                    if user_input.lower() == "w":  # The user needs more time
                        user_input = input("> ").strip()
                    PrintStyle(font_color="white", padding=False, log_only=True).print(f"> {user_input}")        

        # Exit the conversation when the user types 'e'
        if user_input.lower() == 'e': break

        # Send message to agent0
        assistant_response = agent.message_loop(user_input)
        
        # Print agent0 response
        PrintStyle(font_color="white", background_color="#1D8348", bold=True, padding=True).print(f"{agent.agent_name}: response:")
        PrintStyle(font_color="white").print(f"{assistant_response}")        

# User intervention during agent streaming
def intervention():
    if Agent.streaming_agent and not Agent.paused:
        Agent.paused = True  # Stop agent streaming
        PrintStyle(background_color="#6C3483", font_color="white", bold=True, padding=True).print(f"User intervention ('e' to leave, empty to continue):")
        
        import readline  # This fixes arrow keys in terminal
        user_input = input("> ").strip()
        PrintStyle(font_color="white", padding=False, log_only=True).print(f"> {user_input}")
        
        if user_input.lower() == 'e': os._exit(0)  # Exit the conversation when the user types 'exit'
        if user_input: Agent.streaming_agent.intervention_message = user_input  # Set intervention message if non-empty
        Agent.paused = False  # Continue agent streaming

# Capture keyboard input to trigger user intervention
def capture_keys():
    global input_lock
    intervent = False
    while True:
        if intervent: intervention()
        intervent = False
        time.sleep(0.1)

        if Agent.streaming_agent:
            with input_lock, raw_input, application_keypad:
                event: InputEvent | None = get_input_event(timeout=0.1)
                if event and (event.shortcut.isalpha() or event.shortcut.isspace()):
                    intervent = True
                    continue

# User input with timeout
def timeout_input(prompt, timeout=10):
    return timed_input.timeout_input(prompt=prompt, timeout=timeout)

if __name__ == "__main__":
    print("Initializing framework...")

    # Start the key capture thread for user intervention during agent streaming
    threading.Thread(target=capture_keys, daemon=True).start()

    # Start the chat
    initialize()
