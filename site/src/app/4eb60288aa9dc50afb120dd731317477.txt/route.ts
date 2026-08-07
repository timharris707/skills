/**
 * IndexNow ownership proof.
 *
 * The protocol requires the key to be retrievable at the host root, and the
 * filename IS the key — so this directory's name is the credential. Rotating it
 * means renaming the directory and updating scripts/indexnow.py.
 *
 * Nothing secret: it proves control of the host, and its whole job is to be
 * publicly fetchable by Bing, Yandex, Seznam and Naver.
 */
export const dynamic = "force-static";

export function GET() {
  return new Response("4eb60288aa9dc50afb120dd731317477", {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
