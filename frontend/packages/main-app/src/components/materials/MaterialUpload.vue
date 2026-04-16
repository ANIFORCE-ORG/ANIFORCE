<script setup lang="ts">
import { ref } from 'vue'

interface UploadedFile {
  id: string
  file: File
  preview: string
  progress: number
  status: 'uploading' | 'success' | 'error'
  error?: string
}

const emit = defineEmits<{
  (e: 'upload-complete', files: UploadedFile[]): void
  (e: 'close'): void
}>()

const isDragging = ref(false)
const uploadedFiles = ref<UploadedFile[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

// 支持的文件类型
const acceptedTypes = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/quicktime']
const acceptedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov']

const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = false

  const files = Array.from(e.dataTransfer?.files || [])
  processFiles(files)
}

const handleFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  processFiles(files)
}

const handleBrowseClick = () => {
  fileInput.value?.click()
}

const processFiles = (files: File[]) => {
  files.forEach(file => {
    // 验证文件类型
    if (!acceptedTypes.includes(file.type)) {
      alert(`不支持的文件类型: ${file.name}`)
      return
    }

    // 验证文件大小 (最大100MB)
    if (file.size > 100 * 1024 * 1024) {
      alert(`文件过大: ${file.name} (最大100MB)`)
      return
    }

    const fileId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const preview = URL.createObjectURL(file)

    const uploadedFile: UploadedFile = {
      id: fileId,
      file,
      preview,
      progress: 0,
      status: 'uploading'
    }

    uploadedFiles.value.push(uploadedFile)

    // 模拟上传进度
    simulateUpload(uploadedFile)
  })
}

const simulateUpload = (file: UploadedFile) => {
  const interval = setInterval(() => {
    file.progress += Math.random() * 30

    if (file.progress >= 100) {
      file.progress = 100
      file.status = 'success'
      clearInterval(interval)
    }
  }, 300)
}

const removeFile = (fileId: string) => {
  const index = uploadedFiles.value.findIndex(f => f.id === fileId)
  if (index !== -1) {
    URL.revokeObjectURL(uploadedFiles.value[index].preview)
    uploadedFiles.value.splice(index, 1)
  }
}

const handleComplete = () => {
  const successFiles = uploadedFiles.value.filter(f => f.status === 'success')
  emit('upload-complete', successFiles)
  handleClose()
}

const handleClose = () => {
  // 清理预览URL
  uploadedFiles.value.forEach(f => URL.revokeObjectURL(f.preview))
  emit('close')
}

const getFileIcon = (file: File): string => {
  if (file.type.startsWith('image/')) return 'image'
  if (file.type.startsWith('video/')) return 'videocam'
  return 'description'
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="handleClose">
    <div class="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
        <h3 class="text-lg font-bold text-slate-900 dark:text-white">上传素材</h3>
        <button
          class="w-8 h-8 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center justify-center transition-colors"
          @click="handleClose"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">close</span>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Upload Area -->
        <div
          class="border-2 border-dashed rounded-lg p-8 text-center transition-colors mb-6"
          :class="isDragging
            ? 'border-primary bg-primary/5'
            : 'border-slate-300 dark:border-slate-600 hover:border-primary/50'"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @drop="handleDrop"
        >
          <span class="material-symbols-outlined text-6xl text-slate-400 dark:text-slate-600 mb-4">
            cloud_upload
          </span>
          <p class="text-sm text-slate-600 dark:text-slate-400 mb-2">
            拖拽文件到此处，或
            <button
              class="text-primary hover:underline font-medium"
              @click="handleBrowseClick"
            >
              点击浏览
            </button>
          </p>
          <p class="text-xs text-slate-500 dark:text-slate-500">
            支持 JPG, PNG, GIF, MP4, MOV 格式，最大 100MB
          </p>
          <input
            ref="fileInput"
            type="file"
            multiple
            :accept="acceptedExtensions.join(',')"
            class="hidden"
            @change="handleFileSelect"
          />
        </div>

        <!-- Uploaded Files List -->
        <div v-if="uploadedFiles.length > 0" class="space-y-3">
          <h4 class="text-sm font-semibold text-slate-900 dark:text-white mb-3">
            已上传文件 ({{ uploadedFiles.length }})
          </h4>
          <div
            v-for="file in uploadedFiles"
            :key="file.id"
            class="flex items-center gap-3 p-3 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50"
          >
            <!-- Preview -->
            <div class="w-16 h-16 rounded-md overflow-hidden bg-slate-200 dark:bg-slate-700 flex-shrink-0">
              <img
                v-if="file.file.type.startsWith('image/')"
                :src="file.preview"
                :alt="file.file.name"
                class="w-full h-full object-cover"
              />
              <div v-else class="w-full h-full flex items-center justify-center">
                <span class="material-symbols-outlined text-2xl text-slate-400">
                  {{ getFileIcon(file.file) }}
                </span>
              </div>
            </div>

            <!-- File Info -->
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-slate-900 dark:text-white truncate mb-1">
                {{ file.file.name }}
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-2">
                {{ formatFileSize(file.file.size) }}
              </div>

              <!-- Progress Bar -->
              <div v-if="file.status === 'uploading'" class="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-primary rounded-full transition-all"
                  :style="{ width: `${file.progress}%` }"
                ></div>
              </div>

              <!-- Status -->
              <div v-else-if="file.status === 'success'" class="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                <span class="material-symbols-outlined text-sm">check_circle</span>
                上传成功
              </div>
              <div v-else-if="file.status === 'error'" class="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                <span class="material-symbols-outlined text-sm">error</span>
                {{ file.error || '上传失败' }}
              </div>
            </div>

            <!-- Remove Button -->
            <button
              class="w-8 h-8 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center transition-colors flex-shrink-0"
              @click="removeFile(file.id)"
            >
              <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-lg">delete</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end gap-3 p-6 border-t border-slate-200 dark:border-slate-700">
        <button
          class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          @click="handleClose"
        >
          取消
        </button>
        <button
          class="px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="uploadedFiles.filter(f => f.status === 'success').length === 0"
          @click="handleComplete"
        >
          完成上传 ({{ uploadedFiles.filter(f => f.status === 'success').length }})
        </button>
      </div>
    </div>
  </div>
</template>
