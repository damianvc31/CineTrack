/**
 * Diccionario de traducción en frontend para géneros de películas y series.
 * Mantiene la base de datos y la API canónicas sin almacenar traducciones en la BD.
 */

export const GENRE_TRANSLATIONS: Record<string, { en: string; es: string }> = {
  Action: { en: 'Action', es: 'Acción' },
  Adventure: { en: 'Adventure', es: 'Aventura' },
  Animation: { en: 'Animation', es: 'Animación' },
  Comedy: { en: 'Comedy', es: 'Comedia' },
  Crime: { en: 'Crime', es: 'Crimen' },
  Documentary: { en: 'Documentary', es: 'Documental' },
  Drama: { en: 'Drama', es: 'Drama' },
  Family: { en: 'Family', es: 'Familia' },
  Fantasy: { en: 'Fantasy', es: 'Fantasía' },
  History: { en: 'History', es: 'Historia' },
  Horror: { en: 'Horror', es: 'Terror' },
  Music: { en: 'Music', es: 'Música' },
  Mystery: { en: 'Mystery', es: 'Misterio' },
  Romance: { en: 'Romance', es: 'Romance' },
  'Science Fiction': { en: 'Sci-Fi', es: 'Ciencia Ficción' },
  'Sci-Fi': { en: 'Sci-Fi', es: 'Ciencia Ficción' },
  'TV Movie': { en: 'TV Movie', es: 'Película de TV' },
  Thriller: { en: 'Thriller', es: 'Suspense' },
  War: { en: 'War', es: 'Bélica' },
  Western: { en: 'Western', es: 'Western' },
  'Action & Adventure': { en: 'Action & Adventure', es: 'Acción y Aventura' },
  Kids: { en: 'Kids', es: 'Infantil' },
  News: { en: 'News', es: 'Noticias' },
  Reality: { en: 'Reality', es: 'Reality' },
  'Sci-Fi & Fantasy': { en: 'Sci-Fi & Fantasy', es: 'Ciencia Ficción y Fantasía' },
  Soap: { en: 'Soap', es: 'Telenovela' },
  Talk: { en: 'Talk', es: 'Entrevistas' },
  'War & Politics': { en: 'War & Politics', es: 'Bélica y Política' },
}

export function translateGenre(name: string, lang: 'en' | 'es' = 'en'): string {
  if (!name) return ''
  const trimmed = name.trim()
  if (GENRE_TRANSLATIONS[trimmed]) {
    return GENRE_TRANSLATIONS[trimmed][lang] || trimmed
  }
  return trimmed
}
