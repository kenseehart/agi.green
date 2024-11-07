import os
from typing import Dict, List
import asyncio
import logging
import time

from crewai import Agent, Task, Crew
from langchain_community.llms import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain, ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

from agi_green.dispatcher import Protocol, protocol_handler
from .rag import load_rag_database

logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)

class CrewProtocol(Protocol):
    '''
    CrewAI protocol with chat history and RAG
    '''
    protocol_id: str = 'crew'

    def __init__(self, parent: Protocol):
        super().__init__(parent)
        self.llm = ChatOpenAI(temperature=0.7)
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="question",
            output_key="answer",
            return_messages=True
        )
        
        # Load RAG database
        docs_dir = os.path.join(os.environ.get('WORKSPACE', ''), 'chat.agi.green', 'static', 'docs')
        try:
            self.vectorstore = load_rag_database(docs_dir)
            logger.info("RAG database loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load RAG database: {e}")
            self.vectorstore = None
        
        # Create ConversationalRetrievalChain
        if self.vectorstore:
            self.conversation = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectorstore.as_retriever(),
                memory=self.memory,
                verbose=True,
                return_source_documents=True,
                combine_docs_chain_kwargs={
                    "prompt": PromptTemplate(
                        input_variables=["context", "question", "chat_history"],
                        template="""Use the following pieces of context and chat history to have a natural conversation. 
                        Treat each question independently based on its content, not assuming it's related to previous questions unless explicitly referenced.

Context: {context}

Chat History: {chat_history}

Current Question: {question}

Response:"""
                    )
                }
            )

    @protocol_handler
    async def on_mq_chat(self, channel_id: str, author: str, content: str):
        '''Handle incoming chat messages'''
        logger.info(f"Received message from {author}: {content}")
        if author == self.context.user.screen_name:
            response = await self.generate_response(content)
            await self.send('mq', 'chat', channel='chat.public', author='CrewAI', content=response)

    async def generate_response(self, user_message: str):
        logger.info(f"Starting response generation for message: {user_message}")
        start_time = time.time()

        try:
            if self.conversation:
                result = await asyncio.to_thread(
                    self.conversation,
                    {"question": user_message}
                )
                response = result['answer']
            else:
                response = "I'm sorry, but I don't have access to the knowledge base at the moment."
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            response = "I encountered an error while processing your message."

        end_time = time.time()
        processing_time = end_time - start_time
        logger.info(f"CrewAI processing took {processing_time:.2f} seconds")
        logger.info(f"Generated response in {processing_time:.2f} seconds: {response}")
        return response

    @protocol_handler
    async def on_crew_add_document(self, content: str, metadata: Dict = None):
        '''Add a document to the RAG system'''
        logger.info("Adding document to RAG system")
        docs = self.text_splitter.create_documents([content], metadatas=[metadata] if metadata else None)
        self.vector_store.add_documents(docs)
        return "Document added successfully"

    async def process_message(self, author, content):
        logger.info(f"Received message from {author}: {content}")
        if author != "CrewAI":
            response = await self.generate_response(content)
            await self.session.send_chat("chat.public", "CrewAI", response)

    async def run(self):
        self.add_task(super().run())

        api_key = os.environ.get("OPENAI_API_KEY", None)
        if api_key is None:
            raise Exception("crewai needs OPENAI_API_KEY environment variable to be set")

    @protocol_handler
    async def on_crew_create_agent(self, agent_id: str, role: str, goal: str, backstory: str):
        '''Create a new agent'''
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=self.llm
        )
        self.agents[agent_id] = agent
        return f"Agent {agent_id} created successfully"

    @protocol_handler
    async def on_crew_create_task(self, task_id: str, description: str, agent_id: str):
        '''Create a new task'''
        if agent_id not in self.agents:
            return f"Error: Agent {agent_id} not found"
        task = Task(
            description=description,
            agent=self.agents[agent_id]
        )
        self.tasks[task_id] = task
        return f"Task {task_id} created successfully"

    @protocol_handler
    async def on_crew_create_crew(self, crew_id: str, task_ids: List[str], agent_ids: List[str]):
        '''Create a new crew'''
        tasks = [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
        agents = [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
        
        if len(tasks) != len(task_ids) or len(agents) != len(agent_ids):
            return "Error: Some tasks or agents were not found"
        
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True
        )
        self.crews[crew_id] = crew
        return f"Crew {crew_id} created successfully"

    @protocol_handler
    async def on_crew_run(self, crew_id: str):
        '''Run a crew'''
        if crew_id not in self.crews:
            return f"Error: Crew {crew_id} not found"
        
        crew = self.crews[crew_id]
        result = await asyncio.to_thread(crew.kickoff)
        return f"Crew {crew_id} execution result: {result}"

    @protocol_handler
    async def on_crew_list_agents(self):
        '''List all agents'''
        return "\n".join([f"{agent_id}: {agent.role}" for agent_id, agent in self.agents.items()])

    @protocol_handler
    async def on_crew_list_tasks(self):
        '''List all tasks'''
        return "\n".join([f"{task_id}: {task.description}" for task_id, task in self.tasks.items()])

    @protocol_handler
    async def on_crew_list_crews(self):
        '''List all crews'''
        return "\n".join([f"{crew_id}: {len(crew.agents)} agents, {len(crew.tasks)} tasks" for crew_id, crew in self.crews.items()])

    async def close(self):
        # Clean up resources if needed
        await super().close()
