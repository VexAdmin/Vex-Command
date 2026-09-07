<template>
  <div class="bars" :style="{ height: height + 'px' }">
    <div
      v-for="(v, i) in values"
      :key="i"
      class="bar"
      :class="{ neg: v < 0 }"
      :style="{ height: barH(v) + '%' }"
      :title="String(v)"
    />
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{ values: number[]; height?: number }>(), { height: 120 })

function barH(v: number): number {
  const max = Math.max(...props.values.map(Math.abs), 1)
  return Math.max(6, Math.round((Math.abs(v) / max) * 100))
}
</script>
