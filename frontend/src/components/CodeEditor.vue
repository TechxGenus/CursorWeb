<template> 
  <div ref="editorContainer" class="editor-container"></div>
  <div v-if="showSuggestionBox" ref="suggestionBox" class="suggestion-box">
    <pre v-html="displaySuggestion"></pre>
    <div class="suggestion-buttons">
      <button v-if="suggestionTrigger === 'inline'" class="accept-button" @click="acceptChange">Accept</button>
      <button v-if="suggestionTrigger === 'inline'" class="reject-button" @click="rejectChange">Reject</button>
    </div>
  </div>
  <div v-if="showChatBox" ref="chatBox" class="chat-box">
    <textarea v-model="chatInput" placeholder="Enter your instruction here..."></textarea>
    <div class="chat-buttons">
      <button class="submit-button" @click="sendInlineChat">Submit</button>
      <button class="close-button" @click="closeChatBox">Close</button>
    </div>
  </div>
  <div class="reset-button-container">
    <button @click="reset">Reset</button>
  </div>
</template>

<script>
import ace from 'ace-builds';
import 'ace-builds/src-noconflict/ext-language_tools';
import { diffChars } from 'diff';

import 'ace-builds/src-noconflict/theme-tomorrow_night';
import 'ace-builds/src-noconflict/mode-python';

export default {
  name: 'CodeEditor',
  props: {
    code: {
      type: String,
      default: ''
    },
    language: {
      type: String,
      default: 'python'
    }
  },
  data() {
    return {
      editor: null,
      displaySuggestion: '',
      replacementText: '',
      showSuggestionBox: false,
      showChatBox: false,
      debounceTimeout: null,
      localStorageKey: 'editorContent',
      chatInput: '',
      currentDiff: [],
      suggestionTrigger: ''
    };
  },
  mounted() {
    this.initAce();
    this.updateDisplaySuggestion();
  },
  methods: {
    initAce() {
      this.editor = ace.edit(this.$refs.editorContainer);
      this.editor.session.setMode(`ace/mode/${this.language}`);
      this.editor.setTheme('ace/theme/tomorrow_night');
      
      const savedCode = localStorage.getItem(this.localStorageKey) || this.code;
      this.editor.setValue(savedCode, -1);

      this.editor.setFontSize(16);
      this.editor.setShowPrintMargin(false);
      this.editor.renderer.setShowGutter(true);
      
      this.positionSuggestionBox();

      // Keybinding to accept suggestion with Tab key
      this.editor.commands.addCommand({
        name: 'acceptSuggestion',
        bindKey: { win: 'Tab', mac: 'Tab' },
        exec: (editor) => {
          if (this.replacementText) {
            const originalText = editor.getValue();

            // Calculate the new cursor position after accepting the suggestion
            // If the text near the cursor position remains unchanged, we do not move the cursor to better align with user expectations.
            const newCursorPosition = this.calculateCursorPosition(originalText, this.replacementText, editor.getCursorPosition());

            editor.setValue(this.replacementText, -1);

            this.updateDisplaySuggestion();
            this.showSuggestionBox = false;
            editor.moveCursorToPosition(newCursorPosition);
          } else {
            editor.execCommand('insertTab');
          }
        },
        readOnly: false
      });

      // Keybinding for inline chat with Ctrl + I
      this.editor.commands.addCommand({
        name: 'openChatBox',
        bindKey: { win: 'Ctrl-I', mac: 'Command-I' },
        exec: () => {
          this.showChatBox = true;
          this.$nextTick(() => {
            this.positionChatBox();
            this.$refs.chatBox.querySelector('textarea').focus();
          });
        },
        readOnly: false
      });

      // Keybinding to close the chat box with Esc
      this.editor.commands.addCommand({
        name: 'closeChatBox',
        bindKey: { win: 'Esc', mac: 'Esc' },
        exec: () => {
          this.showChatBox = false;
        },
        readOnly: false
      });

      this.editor.on('changeSelection', () => {
        this.positionSuggestionBox();
      });

      this.editor.session.on('change', () => {
        clearTimeout(this.debounceTimeout);
        this.debounceTimeout = setTimeout(() => {
          this.updateDisplaySuggestion();
          localStorage.setItem(this.localStorageKey, this.editor.getValue());
        }, 300);
      });
    },
    positionSuggestionBox() {
      if (!this.editor) return;

      const cursor = this.editor.getCursorPosition();
      const screenPosition = this.editor.renderer.textToScreenCoordinates(cursor.row, cursor.column);
      const editorWidth = this.$refs.editorContainer.clientWidth;

      const suggestionBoxLeft = Math.min(screenPosition.pageX, editorWidth - 200);

      if (this.$refs.suggestionBox) {
        this.$refs.suggestionBox.style.position = 'absolute';
        this.$refs.suggestionBox.style.left = `${suggestionBoxLeft}px`;
        this.$refs.suggestionBox.style.top = `${screenPosition.pageY + 20}px`;
      }
    },
    positionChatBox() {
      if (!this.editor) return;

      const cursor = this.editor.getCursorPosition();
      const screenPosition = this.editor.renderer.textToScreenCoordinates(cursor.row, cursor.column);
      const editorWidth = this.$refs.editorContainer.clientWidth;

      const chatBoxLeft = Math.min(screenPosition.pageX, editorWidth - 310);

      if (this.$refs.chatBox) {
        this.$refs.chatBox.style.position = 'absolute';
        this.$refs.chatBox.style.left = `${chatBoxLeft}px`;
        this.$refs.chatBox.style.top = `${screenPosition.pageY + 50}px`;
      }
    },
    async sendInlineChat() {
      const selectionRange = this.editor.getSelectionRange();
      const start = this.editor.session.getDocument().positionToIndex(selectionRange.start);
      const end = this.editor.session.getDocument().positionToIndex(selectionRange.end);
      const area = [start, end];
      const codeContent = this.editor.getValue();
      const instruction = this.chatInput;

      try {
        const response = await fetch('http://localhost:8000/api/inline', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ code: codeContent, area: area, instruction })
        });

        if (response.ok) {
          const data = await response.json();
          this.replacementText = data.assistant;
          this.displaySuggestion = this.renderSuggestion(codeContent, data.assistant);
          this.currentDiff = this.getLevenshteinChanges(codeContent, data.assistant);
          this.showSuggestionBox = true;
          this.suggestionTrigger = 'inline'; // Set the trigger to 'inline'
          this.$nextTick(() => {
            this.positionSuggestionBox();
          });
        } else {
          console.error('Failed to fetch modified code', response.statusText);
        }
      } catch (error) {
        console.error('Error while sending chat command:', error);
      } finally {
        this.showChatBox = false;
      }
    },
    async updateDisplaySuggestion() {
      const codeContent = this.editor.getValue();
      const selectionRange = this.editor.getSelectionRange();
      const start = this.editor.session.getDocument().positionToIndex(selectionRange.start);
      const end = this.editor.session.getDocument().positionToIndex(selectionRange.end);
      const area = [start, end];

      try {
        const response = await fetch('http://localhost:8000/api/tab', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ code: codeContent, area: area })
        });

        if (response.ok) {
          const data = await response.json();
          this.replacementText = data.assistant;
          this.displaySuggestion = this.renderSuggestion(codeContent, data.assistant);
          this.currentDiff = this.getLevenshteinChanges(codeContent, data.assistant);

          if (this.replacementText !== codeContent && this.editor.getValue() === codeContent) {
            this.showSuggestionBox = true;
            this.suggestionTrigger = 'tab'; // Set the trigger to 'tab'
            this.$nextTick(() => {
              this.positionSuggestionBox();
            });
          } else {
            this.showSuggestionBox = false;
          }
        } else {
          console.error('Failed to fetch suggestion', response.statusText);
          this.showSuggestionBox = false;
        }
      } catch (error) {
        console.error('Error while fetching suggestion:', error);
        this.showSuggestionBox = false;
      }
    },
    acceptChange() {
      this.editor.setValue(this.replacementText, -1);
      this.showSuggestionBox = false;
    },
    rejectChange() {
      this.showSuggestionBox = false;
    },
    closeChatBox() {
      this.showChatBox = false;
    },
    calculateCursorPosition(originalText, newText, cursorPosition) {
      const originalLines = originalText.split('\n');
      const newLines = newText.split('\n');

      let originalOffset = 0;
      for (let i = 0; i < cursorPosition.row; i++) {
        originalOffset += originalLines[i].length + 1;
      }
      originalOffset += cursorPosition.column;

      const changes = this.getLevenshteinChanges(originalText, newText);
      let newOffset = originalOffset;

      for (const change of changes) {
        if (originalOffset >= change.start && originalOffset <= change.end) {
          newOffset = change.newEnd;
          break;
        } else if (originalOffset > change.end) {
          newOffset += change.newEnd - change.end - (change.newStart - change.start);
        }
      }

      let newRow = 0;
      let newColumn = newOffset;
      for (let i = 0; i < newLines.length; i++) {
        if (newColumn <= newLines[i].length) {
          newRow = i;
          break;
        }
        newColumn -= newLines[i].length + 1;
      }

      return { row: newRow, column: newColumn };
    },
    getLevenshteinChanges(original, modified) {
      const changes = diffChars(original, modified);
      const result = [];
      let originalIndex = 0;
      let modifiedIndex = 0;

      changes.forEach(change => {
        if (change.added) {
          result.push({
            start: originalIndex,
            end: originalIndex,
            newStart: modifiedIndex,
            newEnd: modifiedIndex + change.value.length
          });
          modifiedIndex += change.value.length;
        } else if (change.removed) {
          result.push({
            start: originalIndex,
            end: originalIndex + change.value.length,
            newStart: modifiedIndex,
            newEnd: modifiedIndex
          });
          originalIndex += change.value.length;
        } else {
          originalIndex += change.value.length;
          modifiedIndex += change.value.length;
        }

        if (result.length > 1) {
          const lastChange = result[result.length - 1];
          const secondLastChange = result[result.length - 2];

          if (lastChange.start === secondLastChange.end && lastChange.newStart === secondLastChange.newEnd) {
            secondLastChange.end = lastChange.end;
            secondLastChange.newEnd = lastChange.newEnd;
            result.pop();
          }
        }
      });

      return result;
    },
    renderSuggestion(originalText, modifiedText) {
      // TODO: We now render it as a character-level diff on the front end.
      // This is not the best way to display it. If there are many changes, the character-based diff display will be very messy. We should use line-based diff instead.
      // Additionally, we should display local changes to make them easier for users to read.
      const changes = diffChars(originalText, modifiedText);
      return changes.map(change => {
        if (change.added) {
          return `<span style="color: green;">${change.value}</span>`;
        } else if (change.removed) {
          return `<span style="text-decoration: line-through; color: red;">${change.value}</span>`;
        } else {
          return change.value;
        }
      }).join('');
    },
    reset() {
      // Clear the editor content
      this.editor.setValue('', -1);
      localStorage.removeItem(this.localStorageKey);

      // Clear chat input and hide suggestion box
      this.chatInput = '';
      this.showSuggestionBox = false;

      // Optionally clear any suggestion data or reset the chat box state
      this.displaySuggestion = '';
      this.replacementText = '';
      this.currentDiff = [];

      // Clear any other chat-related state
      this.showChatBox = false;

      // Make an API call to reset any backend state if necessary
      fetch('http://localhost:8000/api/reset', {
        method: 'POST'
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === true) {
          console.log('Chat has been reset.');
        } else {
          console.error('Failed to reset chat:', data);
        }
      })
      .catch(error => {
        console.error('Error while resetting chat:', error);
      });
    }
  },
  beforeUnmount() {
    if (this.editor) {
      this.editor.destroy();
      this.editor.container.remove();
    }
  }
}
</script>


<style scoped>
.editor-container {
  height: 100%;
  width: 100%;
  background-color: #1e1e1e;
  color: #d4d4d4;
  font-size: 16px;
}

.editor-container ::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.editor-container ::-webkit-scrollbar-thumb {
  background-color: #3c3c3c;
  border-radius: 4px;
}

.editor-container ::-webkit-scrollbar-thumb:hover {
  background-color: #5a5a5a;
}

.editor-container ::-webkit-scrollbar-track {
  background-color: #1e1e1e;
  border-radius: 4px;
}

.suggestion-box {
  position: absolute;
  background-color: #2a2a2a;
  color: #d4d4d4;
  border: 1px solid #3c3c3c;
  padding: 5px;
  white-space: pre-wrap;
  z-index: 10;
  font-family: 'Courier New', monospace;
  font-size: 16px;
  opacity: 0.9;
}

.chat-box {
  position: absolute;
  background-color: #2a2a2a;
  border: 1px solid #3c3c3c;
  padding: 10px;
  width: 300px;
  z-index: 10;
}

.chat-box textarea {
  width: 100%;
  height: 80px;
  font-size: 14px;
  margin-bottom: 10px;
  padding: 5px;
  resize: none;
  background-color: #1e1e1e;
  color: #d4d4d4;
  border: 1px solid #3c3c3c;
  outline: none;
}

.reset-button-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 100;
}

.reset-button-container button {
  background-color: #6c757d;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  outline: none;
  transition: background-color 0.3s ease;
}

.reset-button-container button:hover {
  opacity: 0.85;
}

.reset-button-container button:active {
  opacity: 0.75;
}

.suggestion-buttons {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.accept-button, .reject-button {
  font-size: 14px;
  padding: 8px 15px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 5px;
}

.accept-button {
  background-color: #28a745; /* Green for accept */
  color: white;
}

.reject-button {
  background-color: #dc3545; /* Red for reject */
  color: white;
}

.chat-buttons {
  display: flex;
  justify-content: flex-end;
}

.submit-button, .close-button {
  font-size: 14px;
  padding: 8px 15px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 5px;
}

.submit-button {
  background-color: #007bff; /* Blue for submit */
  color: white;
}

.close-button {
  background-color: #6c757d; /* Grey for close */
  color: white;
}

button:hover {
  opacity: 0.85;
}

button:active {
  opacity: 0.75;
}

button {
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  outline: none;
  transition: background-color 0.3s ease;
}

</style>
