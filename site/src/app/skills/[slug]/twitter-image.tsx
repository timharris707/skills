/**
 * X reads twitter:image and has been seen ignoring the og:image fallback, so
 * the card ships under both names. Same render, one implementation.
 */
export { default, size, contentType, alt, generateStaticParams } from "./opengraph-image";
