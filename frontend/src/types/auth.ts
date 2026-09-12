export interface UserLogin {
  nombre_usuario: string
  password: string
}

export interface UserRegister {
  nombre_usuario: string
  password: string
  pais?: string | null
  ciudad?: string | null
  descripcion?: string | null
  avatar_url?: string | null
}

export interface UserResponse {
  id: number
  nombre_usuario: string
  pais?: string | null
  ciudad?: string | null
  descripcion?: string | null
  avatar_url?: string | null
  es_admin: boolean
  fecha_registro: string
}

export type User = UserResponse
export type LoginCredentials = UserLogin
export type RegisterCredentials = UserRegister

export interface UserProfileUpdate {
  pais?: string | null
  ciudad?: string | null
  descripcion?: string | null
  avatar_url?: string | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserResponse
}
