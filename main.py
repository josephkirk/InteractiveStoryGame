from typing import Dict, Any, List
from langchain_ollama import OllamaLLM as Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory
import json

class Character:
    def __init__(self, name: str, personality: str, background: str, model: str = "llama3.2"):
        self.name = name
        self.personality = personality
        self.background = background
        self.memory = ConversationBufferMemory(
            return_messages=True
        )
        
        # Character-specific LLM
        self.llm = Ollama(model=model)
        
        # Character response template
        self.response_template = PromptTemplate(
            input_variables=["character_info", "situation", "input", "history"],
            template="""
            You are playing the role of a character with the following traits:
            {character_info}
            
            Current situation: {situation}
            
            Previous conversation:
            {history}
            
            Respond to: {input}
            
            Respond in character, expressing emotions and staying true to your personality.
            """
        )
        
        # Create chain without message history wrapper
        self.chain = (
            RunnablePassthrough.assign(
                history=lambda x: self.memory.load_memory_variables({})["history"]
            )
            | self.response_template
            | self.llm
        )

    def respond(self, situation: str, input_text: str) -> str:
        character_info = f"""
        Name: {self.name}
        Personality: {self.personality}
        Background: {self.background}
        """
        
        response = self.chain.invoke({
            "character_info": character_info,
            "situation": situation,
            "input": input_text
        })
        
        # Save the interaction to memory
        self.memory.save_context(
            {"input": input_text},
            {"output": response}
        )
        
        return response

class NarrativeEngine:
    def __init__(self, model: str = "llama3.2"):
        self.llm = Ollama(model=model)
        
        # Story progression template
        self.progression_template = PromptTemplate(
            input_variables=["story_state", "character_actions", "theme"],
            template="""
            Current story state:
            {story_state}
            
            Recent character actions:
            {character_actions}
            
            Story theme: {theme}
            
            Generate 3 possible story developments as JSON with the following structure:
            {
                "developments": [
                    {
                        "description": "Description of what happens",
                        "new_situation": "The new situation characters find themselves in",
                        "possible_actions": ["Action 1", "Action 2", "Action 3"]
                    }
                ]
            }
            
            Keep developments consistent with the theme and previous events.
            """
        )
        
        # Create LCEL chain with JSON output parser
        self.json_parser = JsonOutputParser()
        self.progression_chain = self.progression_template.pipe(self.llm).pipe(self.json_parser)

    def generate_developments(self, story_state: str, character_actions: str, theme: str) -> Dict[str, List[Dict[str, Any]]]:
        try:
            response = self.progression_chain.invoke({
                "story_state": story_state,
                "character_actions": character_actions,
                "theme": theme
            })
            return response
        except Exception as e:
            return {
                "developments": [{
                    "description": "Error generating developments",
                    "new_situation": story_state,
                    "possible_actions": ["Try again"]
                }]
            }

def create_story_scene():
    # Initialize characters
    protagonist = Character(
        name="Sarah Chen",
        personality="Determined, analytical, but carries emotional wounds from past failures",
        background="Former tech CEO, now investigating mysterious AI phenomena"
    )
    
    antagonist = Character(
        name="Dr. Marcus Webb",
        personality="Brilliant but morally ambiguous, believes the ends justify the means",
        background="AI researcher working on consciousness transfer"
    )
    
    # Initialize narrative engine
    narrative = NarrativeEngine()
    
    # Initial story state
    story_state = """
    Location: Abandoned AI research facility
    Time: Night
    Current situation: Sarah has discovered evidence of illegal AI experiments
    """
    
    # Example interaction
    while True:
        # Generate possible developments
        developments = narrative.generate_developments(
            story_state=story_state,
            character_actions="Sarah examining computer records, Dr. Webb lurking in shadows",
            theme="The ethical limits of scientific progress"
        )
        
        # Present options to the player
        print("\nPossible actions:")
        for i, dev in enumerate(developments["developments"]):
            print(f"{i+1}. {dev['description']}")
        
        # Get player choice
        while True:
            try:
                choice = int(input("\nChoose an action (1-3): ")) - 1
                if 0 <= choice <= 2:
                    break
                print("Please enter a number between 1 and 3")
            except ValueError:
                print("Please enter a valid number")
        chosen_development = developments["developments"][choice]
        
        # Update story state
        story_state = chosen_development["new_situation"]
        
        # Generate character responses
        protagonist_response = protagonist.respond(story_state, chosen_development["description"])
        antagonist_response = antagonist.respond(story_state, protagonist_response)
        
        # Display results
        print(f"\nSarah: {protagonist_response}")
        print(f"\nDr. Webb: {antagonist_response}")
        
        # Option to continue
        if input("\nContinue story? (y/n): ").lower() != 'y':
            break

if __name__ == "__main__":
    create_story_scene()