<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <img src="/vex-logo.svg" alt="VEX" />
        <div>
          <strong>VEX Command</strong>
          <div class="login-sub">Operaciones de plataforma</div>
        </div>
      </div>
      <h1>Entrar</h1>
      <p class="login-lede">Usa tu usuario de operador VEX.</p>
      <form class="login-form" @submit.prevent="submit">
        <label>
          Email
          <input v-model="email" type="email" autocomplete="username" required />
        </label>
        <label>
          Contraseña
          <input v-model="password" type="password" autocomplete="current-password" required />
        </label>
        <p v-if="error" class="login-error">{{ error }}</p>
        <button class="btn primary login-btn" type="submit" :disabled="loading">
          {{ loading ? 'Entrando…' : 'Entrar' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '@/api/client'

const router = useRouter()
const route = useRoute()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await login(email.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect || '/')
  } catch (e) {
    error.value = e instanceof Error && e.message.includes('403')
      ? 'No tienes acceso de operador.'
      : 'Email o contraseña incorrectos.'
  } finally {
    loading.value = false
  }
}
</script>
