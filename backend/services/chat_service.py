from chatbot.query_handler import QueryHandler

class ChatService:
    def __init__(self, rag_data_folder):
        self.query_handler = QueryHandler(rag_data_folder)

    def handle_chat_query(self, user_query):
        response = self.query_handler.handle_query(user_query)
        return {'response': response}
