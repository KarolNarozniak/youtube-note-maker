export const timestamp = (seconds: number): string => {
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours) return `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  return `${minutes}:${String(secs).padStart(2, "0")}`;
};

export const thumbnail = (youtubeId: string): string => `https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`;

export const formatDate = (value: string): string => new Date(value).toLocaleString();
