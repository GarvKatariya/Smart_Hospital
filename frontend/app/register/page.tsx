'use client';
import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Hospital, User, Mail, Lock, Phone } from 'lucide-react';
import { Alert } from '@/components/ui/Alert';

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { register } = useAuth();
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        full_name: formData.full_name,
        email: formData.email,
        password: formData.password,
        phone: formData.phone,
        role: 'patient',
      };
      await register(payload);
      router.push('/dashboard');
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setError(typeof detail === 'string' ? detail : 'Registration failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4 py-12">
      <Card className="w-full max-w-lg">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
            <Hospital className="h-6 w-6 text-blue-600" />
          </div>
          <CardTitle className="text-2xl font-bold">Create Account</CardTitle>
          <CardDescription>Join SmartHospital for better healthcare management</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && <Alert variant="error">{error}</Alert>}

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Input
                  label="Full Name" name="full_name" value={formData.full_name}
                  onChange={handleChange} icon={<User size={18} />} required
                />
              </div>
              <div className="col-span-2">
                <Input
                  label="Email Address" type="email" name="email" value={formData.email}
                  onChange={handleChange} icon={<Mail size={18} />} required
                />
              </div>
              <div className="col-span-1">
                <Input
                  label="Password" type="password" name="password" value={formData.password}
                  onChange={handleChange} icon={<Lock size={18} />} required
                />
              </div>
              <div className="col-span-1">
                <Input
                  label="Confirm Password" type="password" name="confirmPassword" value={formData.confirmPassword}
                  onChange={handleChange} icon={<Lock size={18} />} required
                />
              </div>
              <div className="col-span-1">
                <Input
                  label="Phone Number (Optional)" name="phone" value={formData.phone}
                  onChange={handleChange} icon={<Phone size={18} />}
                />
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" isLoading={isSubmitting}>
              Create Account
            </Button>
            <p className="text-center text-sm text-gray-500">
              Already have an account? <Link href="/login" className="text-blue-600 hover:underline">Sign in</Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
