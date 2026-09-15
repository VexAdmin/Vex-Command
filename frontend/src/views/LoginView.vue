<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <img src="/vex-logo.svg" alt="VEX" />
        <div>
          <strong>Vex Command</strong>
          <div class="login-sub">Founder Console · ops internal</div>
        </div>
      </div>
      <h1>Sign in</h1>
      <p class="login-lede">Use your platform operator credentials (same as Raptor).</p>
      <form class="login-form" @submit.prevent="submit">
        <label>
          Email
          <input v-model="email" type="email" autocomplete="username" required />
        </label>
        <label>
          Password
          <input v-model="password" type="password" autocomplete="current-password" required />
        </label>
        <p v-if="error" class="login-error">{{ error }}</p>
        <button class="btn primary login-btn" type="submit" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign in' }}
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
      ? 'Platform operator access required.'
      : 'Invalid email or password.'
  } finally {
    loading.value = false
  }
}
</script>
