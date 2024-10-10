<template>
  <div id="app" class="dark-theme">
    <ChatInterface />
  </div>
</template>

<script>
import ChatInterface from './components/ChatInterface.vue'

export default {
  name: 'App',
  components: {
    ChatInterface
  }
}
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: Arial, sans-serif;
}

.dark-theme {
  background-color: #1e1e1e;
  color: #ffffff;
  min-height: 100vh;
}
</style>
