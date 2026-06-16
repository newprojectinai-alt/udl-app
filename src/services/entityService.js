import { getStore, setStore } from '@/services/localStore';
import { USE_BACKEND } from '@/services/apiClient';
import {
  backendAssessmentService,
  backendLessonService,
  backendStudentService,
  backendTeacherService,
  backendTextbookService,
} from '@/services/backendServices';

const id = (entityName) => `${entityName.toLowerCase()}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const matches = (record, criteria = {}) =>
  Object.entries(criteria).every(([key, value]) => value === undefined || record[key] === value);

const sortRecords = (records, sort) => {
  if (!sort) return records;
  const descending = sort.startsWith('-');
  const field = descending ? sort.slice(1) : sort;
  return [...records].sort((a, b) => {
    const left = a[field] || '';
    const right = b[field] || '';
    if (left < right) return descending ? 1 : -1;
    if (left > right) return descending ? -1 : 1;
    return 0;
  });
};

export function createEntityService(entityName) {
  return {
    async list(sort, limit) {
      const store = getStore();
      const records = sortRecords(store[entityName] || [], sort);
      return typeof limit === 'number' ? records.slice(0, limit) : records;
    },
    async filter(criteria = {}, sort, limit) {
      const store = getStore();
      const records = sortRecords((store[entityName] || []).filter((record) => matches(record, criteria)), sort);
      return typeof limit === 'number' ? records.slice(0, limit) : records;
    },
    async create(data) {
      const store = getStore();
      const record = { id: id(entityName), created_date: new Date().toISOString(), ...data };
      store[entityName] = [record, ...(store[entityName] || [])];
      setStore(store);
      return record;
    },
    async update(recordId, data) {
      const store = getStore();
      store[entityName] = (store[entityName] || []).map((record) =>
        record.id === recordId ? { ...record, ...data, updated_date: new Date().toISOString() } : record
      );
      setStore(store);
      return store[entityName].find((record) => record.id === recordId);
    },
    async delete(recordId) {
      const store = getStore();
      store[entityName] = (store[entityName] || []).filter((record) => record.id !== recordId);
      setStore(store);
      return true;
    },
  };
}

const localTextbookService = createEntityService('Textbook');
const localStudentService = createEntityService('StudentProfile');
const localTeacherService = createEntityService('TeacherProfile');
const localLessonService = createEntityService('LessonContent');
const localAssessmentService = createEntityService('Assessment');

export const textbookService = USE_BACKEND ? backendTextbookService : localTextbookService;
export const studentService = USE_BACKEND ? backendStudentService : localStudentService;
export const teacherService = USE_BACKEND ? backendTeacherService : localTeacherService;
export const lessonService = USE_BACKEND ? backendLessonService : localLessonService;
export const assessmentService = USE_BACKEND ? backendAssessmentService : localAssessmentService;

export const dataServices = USE_BACKEND
  ? {
      textbookService: backendTextbookService,
      studentService: backendStudentService,
      teacherService: backendTeacherService,
      lessonService: backendLessonService,
      assessmentService: backendAssessmentService,
    }
  : {
      textbookService: localTextbookService,
      studentService: localStudentService,
      teacherService: localTeacherService,
      lessonService: localLessonService,
      assessmentService: localAssessmentService,
    };
