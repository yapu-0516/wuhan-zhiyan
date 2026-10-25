// ESLint 9 扁平配置：Vue 必需规则 + TypeScript 推荐规则，格式化交给 Prettier
import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import prettier from 'eslint-config-prettier'

export default tseslint.config(
  {
    ignores: ['dist/**', 'node_modules/**', 'public/**', 'coverage/**']
  },
  ...tseslint.configs.recommended,
  // Vue 配置放在 TS 之后，确保 .vue 使用 vue-eslint-parser（内部再交给 TS parser）
  ...pluginVue.configs['flat/essential'],
  prettier,
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: { parser: tseslint.parser }
    }
  },
  {
    rules: {
      // 页面组件按业务命名（Dashboard / EventCenter 等），不强制多词
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-empty-object-type': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-console': 'off'
    }
  }
)
