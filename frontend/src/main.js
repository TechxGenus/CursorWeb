import { createApp } from 'vue'
import App from './App.vue'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const app = createApp(App)

app.directive('highlight', function (el) {
  let blocks = el.querySelectorAll('pre code')
  blocks.forEach((block) => {
    hljs.highlightBlock(block)
  })
})

app.mount('#app')
