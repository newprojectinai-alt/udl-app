import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { textbookService } from '@/services/entityService';
import { extractChaptersFromTextbook } from '@/services/aiService';
import { AlertCircle, BookOpen, CheckCircle, Clock, RefreshCw, Trash2, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';

const CLASSES = ['5', '6', '7', '8', '9', '10'];
const SUBJECTS = ['Mathematics', 'Science', 'English', 'Social Studies', 'Hindi', 'Computer Science'];

export default function TextbookUpload() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ title: '', class_level: '', subject: '' });
  const [file, setFile] = useState(null);
  const [textContent, setTextContent] = useState('');
  const [uploading, setUploading] = useState(false);
  const { data: textbooks = [] } = useQuery({
    queryKey: ['textbooks'],
    queryFn: () => textbookService.list('-created_date', 50),
    refetchInterval: (query) => query.state.data?.some((textbook) => textbook.status === 'processing') ? 5000 : false,
  });
  const deleteMutation = useMutation({ mutationFn: (id) => textbookService.delete(id), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['textbooks'] }); toast.success('Textbook deleted'); } });

  const handleUpload = async () => {
    if ((!file && !textContent.trim()) || !form.title || !form.class_level || !form.subject) {
      return toast.error('Please fill all fields and upload a PDF/image or paste textbook text');
    }
    setUploading(true);
    if (textbookService.uploadPdf) {
      await textbookService.uploadPdf({ file, ...form, text_content: textContent, uploaded_by: 'admin@udl.local' });
    } else {
      const record = await textbookService.create({ ...form, file_url: file ? URL.createObjectURL(file) : '', extracted_text: textContent, status: 'processing' });
      const chapters = await extractChaptersFromTextbook(form);
      await textbookService.update(record.id, { chapters, status: 'ready' });
    }
    queryClient.invalidateQueries({ queryKey: ['textbooks'] });
    setForm({ title: '', class_level: '', subject: '' });
    setFile(null);
    setTextContent('');
    setUploading(false);
    toast.success('Textbook uploaded and processed');
  };

  const statusIcon = (status) => status === 'ready' ? <CheckCircle className="w-4 h-4 text-emerald-500" /> : status === 'error' ? <AlertCircle className="w-4 h-4 text-red-500" /> : <Clock className="w-4 h-4 text-amber-500" />;

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto">
      <div className="mb-8"><h1 className="font-poppins font-bold text-2xl">Upload Textbooks</h1><p className="text-muted-foreground text-sm mt-1">Upload PDF textbooks and generate chapter lists locally</p></div>
      <div className="bg-card border border-border rounded-2xl p-6 mb-8 space-y-4">
        <h2 className="font-semibold">Add New Textbook</h2>
        <div className="grid md:grid-cols-3 gap-4"><div><Label>Title</Label><Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></div><div><Label>Class</Label><Select value={form.class_level} onValueChange={(value) => setForm({ ...form, class_level: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{CLASSES.map((item) => <SelectItem key={item} value={item}>Class {item}</SelectItem>)}</SelectContent></Select></div><div><Label>Subject</Label><Select value={form.subject} onValueChange={(value) => setForm({ ...form, subject: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{SUBJECTS.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div></div>
        <div>
          <Label>PDF or Image File</Label>
          <input className="mt-2 block text-sm" type="file" accept=".pdf,image/*" onChange={(event) => setFile(event.target.files?.[0])} />
          {file && <p className="text-xs text-primary mt-1">{file.name}</p>}
          <p className="text-xs text-muted-foreground mt-1">Images use OCR. For fastest results, paste text below instead of uploading scanned pages.</p>
        </div>
        <div>
          <Label>Paste Textbook Content / Chapter Text</Label>
          <textarea
            value={textContent}
            onChange={(event) => setTextContent(event.target.value)}
            placeholder="Paste textbook text here. AI will use this text to create Basic, Standard, or Advanced lessons based on each student profile."
            className="mt-2 w-full min-h-36 rounded-xl border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <p className="text-xs text-muted-foreground mt-1">This is the fastest and most reliable option. The student lesson AI adapts this content to their selected level.</p>
        </div>
        <Button onClick={handleUpload} disabled={uploading}>{uploading ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Processing…</> : <><Upload className="w-4 h-4 mr-2" />Upload & Process</>}</Button>
      </div>
      <div className="bg-card border border-border rounded-2xl p-6"><h2 className="font-semibold mb-4">All Textbooks ({textbooks.length})</h2><div className="space-y-3">{textbooks.map((item) => <div key={item.id} className="flex items-center justify-between p-4 rounded-xl border border-border"><div className="flex items-center gap-4"><BookOpen className="w-5 h-5 text-primary" /><div><p className="font-medium text-sm">{item.title}</p><p className="text-xs text-muted-foreground">{item.subject} · {item.chapters?.length || 0} chapters</p></div></div><div className="flex items-center gap-3">{statusIcon(item.status)}<Button variant="ghost" size="icon" onClick={() => deleteMutation.mutate(item.id)}><Trash2 className="w-4 h-4" /></Button></div></div>)}</div></div>
    </div>
  );
}
