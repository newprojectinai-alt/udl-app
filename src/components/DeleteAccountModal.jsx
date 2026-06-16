import { useState } from 'react';
import { AlertTriangle, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/AuthContext';
import { studentService } from '@/services/entityService';
import { toast } from 'sonner';

export default function DeleteAccountModal() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    if (!confirmed || !user?.email) return;
    setLoading(true);
    const profiles = await studentService.filter({ user_email: user.email });
    await Promise.all(profiles.map((profile) => studentService.delete(profile.id)));
    toast.success('Account data deleted. You will be signed out.');
    setTimeout(logout, 800);
    setLoading(false);
  };

  if (!open) {
    return (
      <div className="mt-8 border border-destructive/30 rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-2"><Trash2 className="w-4 h-4 text-destructive" /><h3 className="font-semibold text-destructive text-sm">Delete Account</h3></div>
        <p className="text-xs text-muted-foreground mb-4">Permanently delete your account profile data.</p>
        <Button variant="destructive" size="sm" onClick={() => setOpen(true)}>Delete My Account</Button>
      </div>
    );
  }

  return (
    <div className="mt-8 border-2 border-destructive rounded-2xl p-5 bg-destructive/5">
      <div className="flex items-start gap-3 mb-4"><AlertTriangle className="w-5 h-5 text-destructive shrink-0" /><p className="text-sm text-muted-foreground">This permanently deletes your local student profile.</p></div>
      <label className="flex items-center gap-2 mb-5 cursor-pointer"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span className="text-sm">I understand this action is permanent</span></label>
      <div className="flex gap-3"><Button variant="outline" size="sm" onClick={() => setOpen(false)}>Cancel</Button><Button variant="destructive" size="sm" disabled={!confirmed || loading} onClick={handleDelete}>{loading ? 'Deleting…' : 'Yes, Delete Everything'}</Button></div>
    </div>
  );
}
