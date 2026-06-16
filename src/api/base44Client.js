import {
  assessmentService,
  lessonService,
  studentService,
  teacherService,
  textbookService,
} from '@/services/entityService';
import { getCurrentUser, logout } from '@/services/authService';
import {
  extractChaptersFromTextbook,
  generateAssessment,
  generateFeedback,
  generateLesson,
} from '@/services/aiService';

export const base44 = {
  auth: {
    me: getCurrentUser,
    logout,
    redirectToLogin: () => {},
  },
  entities: {
    Assessment: assessmentService,
    LessonContent: lessonService,
    StudentProfile: studentService,
    TeacherProfile: teacherService,
    Textbook: textbookService,
  },
  integrations: {
    Core: {
      UploadFile: async ({ file }) => ({ file_url: file ? URL.createObjectURL(file) : '' }),
      InvokeLLM: async ({ prompt }) => {
        if (prompt?.includes('list the chapter')) return { chapters: await extractChaptersFromTextbook({ title: prompt }) };
        if (prompt?.includes('Create a detailed')) return generateLesson({});
        if (prompt?.includes('questions')) return generateAssessment({});
        return generateFeedback({ assessment: { subject: 'Lesson', chapter: 'Topic' }, score: 0, totalQuestions: 1, percentage: 0 });
      },
    },
  },
};
