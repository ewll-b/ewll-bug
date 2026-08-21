<script setup lang="ts">
import zhCN from '@arco-design/web-vue/es/locale/lang/zh-cn'
import AppShell from './layouts/AppShell.vue'
</script>

<template>
  <a-config-provider :locale="zhCN" size="medium">
    <router-view v-slot="{ Component, route }">
      <component :is="Component" v-if="route.meta.public === true" />
      <AppShell v-else><component :is="Component" /></AppShell>
    </router-view>
  </a-config-provider>
</template>
