'use client';

import { FormEvent, useState } from 'react';
import axios from 'axios';
import { User, Mail, Shield } from 'lucide-react';
import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/lib/auth';
import { getRoleColor } from '@/lib/utils';

export default function ProfilePage() {
  const { user, updateProfile, changePassword } = useAuth();
  const [fullName, setFullName] = useState<string | null>(null);
  const [phone, setPhone] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  const profileName = fullName ?? user?.full_name ?? '';
  const profilePhone = phone ?? user?.phone ?? '';

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setProfileError('');
    setProfileSuccess('');
    setSavingProfile(true);
    try {
      await updateProfile({ full_name: profileName, phone: profilePhone });
      setProfileSuccess('Your profile has been updated.');
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setProfileError(typeof detail === 'string' ? detail : 'Could not update your profile.');
    } finally {
      setSavingProfile(false);
    }
  };

  const savePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');
    if (newPassword !== confirmPassword) {
      setPasswordError('The new password and confirmation do not match.');
      return;
    }
    setSavingPassword(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordSuccess('Your password has been updated.');
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setPasswordError(typeof detail === 'string' ? detail : 'Could not update your password.');
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">My Profile</h2>
        <p className="text-muted-foreground">Manage your account details and password.</p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center space-x-4 pb-6">
          <div className="flex h-20 w-20 items-center justify-center rounded-full border-4 border-white bg-blue-100 shadow-sm">
            <User className="h-10 w-10 text-blue-600" />
          </div>
          <div>
            <CardTitle className="text-2xl">{user?.full_name ?? 'Loading profile…'}</CardTitle>
            <div className="mt-1 flex items-center gap-2">
              <Mail className="h-4 w-4 text-gray-500" />
              <span className="text-sm text-gray-500">{user?.email}</span>
              {user?.role && <Badge variant={getRoleColor(user.role)} className="ml-2 uppercase">{user.role}</Badge>}
            </div>
          </div>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Personal Information</CardTitle>
          <CardDescription>Update your name and phone number.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={saveProfile} className="space-y-4">
            {profileError && <Alert variant="error">{profileError}</Alert>}
            {profileSuccess && <Alert variant="success">{profileSuccess}</Alert>}
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Full Name" value={profileName} onChange={event => setFullName(event.target.value)} required />
              <Input label="Phone Number" value={profilePhone} onChange={event => setPhone(event.target.value)} placeholder="Add phone number" />
              <Input label="Email Address" value={user?.email ?? ''} disabled />
            </div>
            <Button type="submit" isLoading={savingProfile}>Save Changes</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center"><Shield className="mr-2 h-5 w-5" />Security Settings</CardTitle>
          <CardDescription>Choose a new password of at least eight characters.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={savePassword} className="max-w-sm space-y-4">
            {passwordError && <Alert variant="error">{passwordError}</Alert>}
            {passwordSuccess && <Alert variant="success">{passwordSuccess}</Alert>}
            <Input label="Current Password" type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} required />
            <Input label="New Password" type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} minLength={8} required />
            <Input label="Confirm New Password" type="password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} minLength={8} required />
            <Button type="submit" variant="outline" isLoading={savingPassword}>Update Password</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
