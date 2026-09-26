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

export type VarietyLevel = 'VERY_LOW' | 'LOW' | 'MEDIUM' | 'HIGH' | 'VERY_HIGH'

export interface UserResponse {
  id: number
  nombre_usuario: string
  pais?: string | null
  ciudad?: string | null
  descripcion?: string | null
  avatar_url?: string | null
  preferencia_variedad_ia?: VarietyLevel
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
  preferencia_variedad_ia?: VarietyLevel
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserResponse
}
