import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { getApiErrorMessage } from '../../core/formatters';

@Component({
  selector: 'app-login-page',
  imports: [FormsModule, RouterLink],
  templateUrl: './login-page.html',
  styleUrl: './login-page.css'
})
export class LoginPageComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected email = '';
  protected password = '';
  protected error = '';
  protected loading = false;

  protected async submit(): Promise<void> {
    if (this.loading) {
      return;
    }

    this.loading = true;
    this.error = '';

    try {
      await this.authService.login({
        email: this.email.trim(),
        password: this.password
      });

      const nextUrl = this.route.snapshot.queryParamMap.get('next') || '/';
      await this.router.navigateByUrl(nextUrl);
    } catch (error) {
      this.error = getApiErrorMessage(error);
    } finally {
      this.loading = false;
    }
  }
}
