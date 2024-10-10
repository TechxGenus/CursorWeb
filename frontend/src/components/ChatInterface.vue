<template>
  <div class="chat-interface">
    <div class="chat-container" :style="{ width: chatWidth + 'px' }">
      <div class="chat-header">
        <h1>CursorWeb</h1>
      </div>
      <div class="chat-messages">
        <div v-for="(message, index) in messages" :key="index" class="message">
          <div
            class="message-content"
            :class="{
              'user-message': message.isUser,
              'bot-message': !message.isUser
            }"
            v-html="renderMarkdown(message.text)"
          ></div>
        </div>
      </div>
      <div class="chat-input">
        <textarea
          v-model="userInput"
          @keyup.enter="sendMessage"
          placeholder="Enter message..."
          rows="1"
        ></textarea>
        <button @click="sendMessage">Send</button>
        <button @click="resetChat" class="reset-button">Reset</button>
      </div>
    </div>
    <div class="editor-container">
      <CodeEditor :code="currentCode" :language="currentLanguage" />
    </div>
  </div>
</template>

<script>
import CodeEditor from './CodeEditor.vue';
import { marked } from 'marked';

export default {
  name: 'ChatInterface',
  components: {
    CodeEditor,
  },
  data() {
    return {
      userInput: '',
      messages: [],
      currentCode: '',
      currentLanguage: 'python',
      chatWidth: 500,
    };
  },
  created() {
    const savedMessages = localStorage.getItem('chatMessages');
    if (savedMessages) {
      this.messages = JSON.parse(savedMessages);
    }
  },
  watch: {
    messages: {
      handler(newMessages) {
        localStorage.setItem('chatMessages', JSON.stringify(newMessages));
      },
      deep: true,
    },
  },
  methods: {
    renderMarkdown(text) {
      return marked(text);
    },
    async sendMessage() {
      if (this.userInput.trim()) {
        this.messages.push({ text: this.userInput, isUser: true });

        const userText = this.userInput;
        this.userInput = '';

        try {
          const response = await fetch('http://localhost:8000/api/chat', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: userText }),
          });

          const data = await response.json();

          this.messages.push({
            text: data.assistant,
            isUser: false,
          });
        } catch (error) {
          console.error('Error sending message:', error);
          this.messages.push({
            text: 'An error occurred while communicating with the server.',
            isUser: false,
          });
        }
      }
    },
    async resetChat() {
      this.messages = [];

      localStorage.removeItem('chatMessages');

      try {
        await fetch('http://localhost:8000/api/reset', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
      } catch (error) {
        console.error('Error resetting chat:', error);
      }
    },
  },
};
</script>

<style scoped>
.chat-interface {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.chat-container {
  display: flex;
  flex-direction: column;
  border-right: 1px solid #444;
  flex-shrink: 0;
}

.chat-header {
  background-color: #2d2d2d;
  padding: 10px;
  text-align: center;
  color: #ffffff;
}

.chat-messages {
  flex-grow: 1;
  overflow-y: auto;
  padding: 10px;
  background-color: #1e1e1e;
  scrollbar-width: thin;
  scrollbar-color: #3a3a3a #1e1e1e;
}

.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background-color: #1e1e1e;
}

.chat-messages::-webkit-scrollbar-thumb {
  background-color: #3a3a3a;
  border-radius: 4px;
}

.message {
  margin-bottom: 10px;
  display: flex;
}

.message-content {
  border-radius: 10px;
  padding: 10px;
  max-width: 80%;
  font-size: 1em;
  line-height: 1.4;
  word-wrap: break-word;
}

.user-message {
  background-color: #0084ff;
  color: #ffffff;
  align-self: flex-end;
  text-align: right;
  margin-left: auto;
}

.bot-message {
  background-color: #444654;
  color: #ffffff;
  align-self: flex-start;
  text-align: left;
  margin-right: auto;
}

.chat-input {
  padding: 10px;
  display: flex;
  background-color: #2d2d2d;
}

.chat-input textarea {
  flex-grow: 1;
  margin-right: 10px;
  padding: 10px;
  border: none;
  border-radius: 5px;
  background-color: #3a3a3a;
  color: #ffffff;
  resize: none;
  overflow-y: auto;
  height: auto;
  max-height: 100px;
  scrollbar-width: thin;
  scrollbar-color: #3a3a3a #2d2d2d;
}

.chat-input textarea::-webkit-scrollbar {
  width: 8px;
}

.chat-input textarea::-webkit-scrollbar-track {
  background-color: #2d2d2d;
}

.chat-input textarea::-webkit-scrollbar-thumb {
  background-color: #3a3a3a;
  border-radius: 4px;
}

.chat-input button {
  padding: 10px 15px;
  background-color: #007bff;
  border: none;
  border-radius: 5px;
  color: #ffffff;
  cursor: pointer;
  margin-left: 5px;
  transition: background-color 0.3s ease;
}

.chat-input button:hover {
  background-color: #0056b3;
}

.chat-input button:active {
  background-color: #004085;
}

.chat-input textarea:focus,
.chat-input button:focus {
  outline: none;
}

.chat-input .reset-button {
  background-color: #6c757d !important;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  outline: none;
  transition: background-color 0.3s ease;
}

.chat-input .reset-button:hover {
  opacity: 0.85;
}

.chat-input .reset-button:active {
  opacity: 0.75;
}

.editor-container {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.message-content pre {
  background-color: #2d2d2d;
  padding: 10px;
  border-radius: 5px;
  overflow-x: auto;
}
</style>
