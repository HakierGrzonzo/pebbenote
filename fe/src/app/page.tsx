import styles from "./page.module.css";
import { listNotes } from "@/client";

export default async function Home() {
  const {data} = await listNotes()
  return (
    <div className={styles.page}>
      {data?.map((note) => (
        <pre key={note.note_id}>{note.content}</pre>
      ))}
    </div>
  );
}
