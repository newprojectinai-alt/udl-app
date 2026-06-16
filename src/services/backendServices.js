import { apiDelete, apiGet, apiPatch, apiPost, apiUpload } from '@/services/apiClient';

const queryString = (params = {}) => {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '');
  return entries.length ? `?${new URLSearchParams(entries).toString()}` : '';
};

export const backendTextbookService = {
  list: () => apiGet('/api/textbooks'),
  filter: (filters) => apiGet(`/api/textbooks${queryString(filters)}`),
  create: (data) => apiPost('/api/textbooks', data),
  update: (id, data) => apiPatch(`/api/textbooks/${id}`, data),
  delete: (id) => apiDelete(`/api/textbooks/${id}`),
  uploadPdf: ({ file, title, class_level, subject, uploaded_by, text_content }) => {
    const formData = new FormData();
    if (file) formData.append('file', file);
    formData.append('title', title);
    formData.append('class_level', class_level);
    formData.append('subject', subject);
    if (uploaded_by) formData.append('uploaded_by', uploaded_by);
    if (text_content) formData.append('text_content', text_content);
    return apiUpload('/api/textbooks/upload', formData);
  },
};

export const backendStudentService = {
  list: () => apiGet('/api/users/students'),
  filter: (filters) => filters?.user_email ? apiGet(`/api/users/students/by-email/${encodeURIComponent(filters.user_email)}`) : apiGet('/api/users/students'),
  create: (data) => apiPost('/api/users/students', data),
  update: (id, data) => apiPatch(`/api/users/students/${id}`, data),
  delete: (id) => apiDelete(`/api/users/students/${id}`),
};

export const backendTeacherService = {
  list: () => apiGet('/api/users/teachers'),
  filter: () => apiGet('/api/users/teachers'),
};

export const backendLessonService = {
  filter: (filters) => apiGet(`/api/lessons${queryString(filters)}`),
  create: (data) => apiPost('/api/lessons/generate', data),
  generate: (data) => apiPost('/api/lessons/generate', data),
};

export const backendAssessmentService = {
  list: () => apiGet('/api/assessments'),
  filter: (filters) => apiGet(`/api/assessments${queryString(filters)}`),
  create: (data) => apiPost('/api/assessments/generate', data),
  update: (id, data) => apiPatch(`/api/assessments/${id}`, data),
  complete: (id, data) => apiPost(`/api/assessments/${id}/complete`, data),
};

export const backendVideoService = {
  generate: (lessonId, options = {}) => apiPost('/api/videos/generate', { lesson_id: lessonId, ...options }),
  latestForLesson: (lessonId) => apiGet(`/api/videos/lesson/${lessonId}/latest`),
  get: (jobId) => apiGet(`/api/videos/${jobId}`),
  render: (jobId) => apiPost(`/api/videos/${jobId}/render`, {}),
};
