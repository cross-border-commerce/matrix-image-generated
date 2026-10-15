import type { TryOnImage } from "../api";

type Props = {
  images: TryOnImage[];
};

export default function ResultGrid({ images }: Props) {
  if (images.length === 0) {
    return null;
  }

  return (
    <div>
      <ul className="result-grid">
        {images.map((image) => (
          <li key={image.url}>
            <img src={image.url} alt={`${image.product} / ${image.model}`} />
            <div className="result-meta">
              <span>
                {image.product} · {image.model}
                {image.logo ? ` · ${image.logo}` : ""}
              </span>
              <a href={image.url} download>
                下载
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
