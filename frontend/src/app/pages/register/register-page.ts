import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { getApiErrorMessage } from '../../core/formatters';

@Component({
  selector: 'app-register-page',
  imports: [FormsModule, RouterLink],
  templateUrl: './register-page.html',
  styleUrl: './register-page.css'
})
export class RegisterPageComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

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
      await this.authService.register({
        email: this.email.trim(),
        password: this.password
      });

      await this.router.navigate(['/verify'], {
        queryParams: {
          email: this.email.trim()
        }
      });
    } catch (error) {
      this.error = getApiErrorMessage(error);
    } finally {
      this.loading = false;
    }
  }
}
