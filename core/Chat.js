<template>
  <div class="neuro-container">
    <!-- Animated Brain -->
    <video 
      v-if="processing" 
      src="./assets/brain.mp4" 
      autoplay loop muted
      class="brain-visualization"
    ></video>
    
    <!-- Chat Interface -->
    <div class="chat-window">
      <div v-for="(msg, i) in messages" :key="i" :class="msg.type">
        {{ msg.text }}
      </div>
    </div>

    <!-- Input -->
    <input 
      v-model="inputText" 
      @keyup.enter="sendMessage"
      placeholder="Engage dialectic analysis..."
      class="darpa-input"
    />
  </div>
</template>

<script>
export default {
  data() {
    return {
      inputText: '',
      messages: [],
      processing: false
    }
  },
  methods: {
    async sendMessage() {
      this.messages.push({ type: 'user', text: this.inputText });
      this.processing = true;
      
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: this.inputText })
      });
      
      const data = await response.json();
      this.messages.push({ type: 'paradox', text: data.response });
      this.processing = false;
      this.inputText = '';
    }
  }
}
</script>

<style scoped>
/* DARPA-style dark theme */
.neuro-container {
  background-color: #0a0a12;
  color: #00ff41;
  font-family: 'Courier New', monospace;
}

.brain-visualization {
  position: absolute;
  width: 300px;
  opacity: 0.7;
  right: 20px;
  top: 20px;
}

.darpa-input {
  background: #111122;
  border: 1px solid #00ff41;
  color: white;
  padding: 10px;
  width: 80%;
}

.user { color: #4fc3f7; }
.paradox { color: #00ff41; }
</style>
