import { Component, ElementRef, QueryList, ViewChildren, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { getApiErrorMessage } from '../../core/formatters';

@Component({
  selector: 'app-verify-page',
  imports: [FormsModule, RouterLink],
  templateUrl: './verify-page.html',
  styleUrl: './verify-page.css'
})
export class VerifyPageComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  @ViewChildren('digitInput')
  private digitInputs!: QueryList<ElementRef<HTMLInputElement>>;

  protected email =
    this.route.snapshot.queryParamMap.get('email') ?? this.authService.pendingEmail() ?? '';
  protected digits = ['', '', '', '', '', ''];
  protected error = '';
  protected success = '';
  protected loading = false;
  protected resendLoading = false;

  protected async submit(): Promise<void> {
    if (this.loading) {
      return;
    }

    const email = this.email.trim();
    const code = this.digits.join('');

    if (!email || code.length < 6) {
      this.error = 'Укажи email и введи шестизначный код полностью.';
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';

    try {
      await this.authService.confirmRegistration(email, code);
      await this.router.navigateByUrl('/');
    } catch (error) {
      this.error = getApiErrorMessage(error);
    } finally {
      this.loading = false;
    }
  }

  protected async resend(): Promise<void> {
    if (this.resendLoading) {
      return;
    }

    const email = this.email.trim();

    if (!email) {
      this.error = 'Сначала введи email, на который нужно отправить код.';
      return;
    }

    this.resendLoading = true;
    this.error = '';
    this.success = '';

    try {
      const response = await this.authService.resendVerifyCode(email);
      this.authService.setPendingEmail(email);
      this.success = response.message;
    } catch (error) {
      this.error = getApiErrorMessage(error);
    } finally {
      this.resendLoading = false;
    }
  }

  protected onDigitInput(index: number, value: string): void {
    const normalized = value.replace(/\D/g, '');

    if (!normalized) {
      this.digits[index] = '';
      return;
    }

    if (normalized.length > 1) {
      this.fillDigits(normalized);
      return;
    }

    this.digits[index] = normalized;

    if (index < this.digits.length - 1) {
      this.focusInput(index + 1);
    }
  }

  protected onDigitKeydown(event: KeyboardEvent, index: number): void {
    if (event.key === 'Backspace' && !this.digits[index] && index > 0) {
      this.focusInput(index - 1);
    }
  }

  protected onPaste(event: ClipboardEvent): void {
    event.preventDefault();
    const pastedText = event.clipboardData?.getData('text')?.replace(/\D/g, '') ?? '';
    this.fillDigits(pastedText);
  }

  private fillDigits(value: string): void {
    const nextDigits = ['', '', '', '', '', ''];

    for (let index = 0; index < nextDigits.length; index += 1) {
      nextDigits[index] = value[index] ?? '';
    }

    this.digits = nextDigits;
    this.focusInput(Math.min(value.length, 5));
  }

  private focusInput(index: number): void {
    queueMicrotask(() => {
      this.digitInputs.get(index)?.nativeElement.focus();
      this.digitInputs.get(index)?.nativeElement.select();
    });
  }
}
