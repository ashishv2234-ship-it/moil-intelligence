import { useState } from 'react'
import { useForm, type SubmitHandler } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth, home } from '../store/auth'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Enter your password'),
})

type LoginForm = z.infer<typeof schema>

export default function Login() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(schema),
  })

  const [err, setErr] = useState('')
  const login = useAuth((s) => s.login)
  const nav = useNavigate()
  const expired = useSearchParams()[0].get('expired')

  const submit: SubmitHandler<LoginForm> = async (d) => {
    setErr('')

    try {
      nav(home[await login(d.email, d.password)])
    } catch (e: any) {
      const m = e.response?.data?.detail
      setErr(
        typeof m === 'string'
          ? m
          : 'Cannot reach the server. Check that the backend is running on port 8000.'
      )
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-ink">
      <form
        onSubmit={handleSubmit(submit)}
        className="w-96 border border-line bg-panel"
      >
        <div className="bg-[#1F2A33] px-6 py-4">
          <h1 className="text-base font-semibold text-white">MOIL Limited</h1>
          <p className="text-xs text-slate-300">
            Mining Intelligence System
          </p>
        </div>

        <div className="space-y-3 p-6">
          <p className="text-sm font-medium">Sign in</p>

          {expired && (
            <p className="text-sm text-warn">
              Your session expired. Sign in again.
            </p>
          )}

          {err && (
            <p role="alert" className="text-sm text-crit">
              {err}
            </p>
          )}

          <input
            {...register('email')}
            placeholder="Email"
            className="w-full rounded border border-line bg-panel px-3 py-2 text-sm"
          />
          <p className="text-xs text-crit">
            {errors.email?.message}
          </p>

          <input
            type="password"
            {...register('password')}
            placeholder="Password"
            className="w-full rounded border border-line bg-panel px-3 py-2 text-sm"
          />
          <p className="text-xs text-crit">
            {errors.password?.message}
          </p>

          <button
            disabled={isSubmitting}
            className="w-full rounded bg-mn py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {isSubmitting ? 'Signing in' : 'Sign in'}
          </button>

          <p className="text-xs text-mute">
            Demo: mine_manager@moil.in / Moil@12345. Other roles use the same
            password, e.g. admin@moil.in.
          </p>
        </div>
      </form>
    </div>
  )
}
