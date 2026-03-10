import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom, Observable } from 'rxjs';

import { SKIP_AUTH_REFRESH } from './auth.interceptor';
import { AuthCredentials, AuthMessage, User } from './models';

const pendingEmailKey = 'glass-selling.pending-email';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);

  readonly user = signal<User | null>(null);
  readonly pendingEmail = signal(localStorage.getItem(pendingEmailKey) ?? '');
  private readonly isBootstrapped = signal(false);
  private profileRequest: Promise<User | null> | null = null;

  bootstrap(): void {
    if (this.isBootstrapped()) {
      return;
    }

    this.isBootstrapped.set(true);
    void this.loadProfile();
  }

  async loadProfile(): Promise<User | null> {
    try {
      const user = await firstValueFrom(this.http.get<User>('/auth/me'));
      this.user.set(user);
      return user;
    } catch {
      this.user.set(null);
      return null;
    }
  }

  async ensureProfile(): Promise<User | null> {
    if (this.user()) {
      return this.user();
    }

    if (this.profileRequest) {
      return this.profileRequest;
    }

    this.profileRequest = this.loadProfile().finally(() => {
      this.profileRequest = null;
    });

    return this.profileRequest;
  }

  async login(credentials: AuthCredentials): Promise<User> {
    const user = await firstValueFrom(this.http.post<User>('/auth/login', credentials));
    this.user.set(user);
    return user;
  }

  async register(credentials: AuthCredentials): Promise<AuthMessage> {
    const response = await firstValueFrom(this.http.post<AuthMessage>('/auth/registration', credentials));
    this.setPendingEmail(response.email ?? credentials.email);
    return response;
  }

  async confirmRegistration(email: string, code: string): Promise<User> {
    const user = await firstValueFrom(this.http.post<User>('/auth/registration/confirm', { email, code }));
    this.user.set(user);
    this.setPendingEmail('');
    return user;
  }

  async resendVerifyCode(email: string): Promise<AuthMessage> {
    return firstValueFrom(
      this.http.post<AuthMessage>('/auth/registration/resend_verify_code', {
        email
      })
    );
  }

  async logout(): Promise<void> {
    try {
      await firstValueFrom(
        this.http.post<void>('/auth/logout', {}, {
          context: new HttpContext().set(SKIP_AUTH_REFRESH, true)
        })
      );
    } finally {
      this.clearSession();
    }
  }

  refreshSession(): Observable<unknown> {
    return this.http.post(
      '/auth/refresh',
      {},
      {
        context: new HttpContext().set(SKIP_AUTH_REFRESH, true)
      }
    );
  }

  setPendingEmail(email: string): void {
    const normalized = email.trim();
    this.pendingEmail.set(normalized);

    if (normalized) {
      localStorage.setItem(pendingEmailKey, normalized);
      return;
    }

    localStorage.removeItem(pendingEmailKey);
  }

  clearSession(): void {
    this.user.set(null);
  }
}
