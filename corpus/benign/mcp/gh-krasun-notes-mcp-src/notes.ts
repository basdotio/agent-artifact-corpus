import { executeOSAScript } from "./osascript";

export type Note = {
    id: string;
    name: string;
    creationDate: string;
    modificationDate: string;
    plaintext: string;
};

export type Folder = {
    id: string;
    name: string;
};

export async function createNote(
    folderId: string,
    note: {
        name: string;
        body: string;
    }
): Promise<Omit<Note, "plaintext">> {
    const escapedName = note.name.replace(/[\\'"]/g, "\\$&");
    const escapedBody = note.body
        .replace(/[\\'"]/g, "\\$&")
        .replace(/\n/g, "\\n")
        .replace(/\r/g, "");
    const result = await executeOSAScript(`
        const Notes = Application('Notes');

        const folder = Notes.folders.whose({ id: '${folderId}' })[0];
        const note = Notes.Note({
            name: "${escapedName}",
            body: "${escapedBody}"
        });

        folder.notes.push(note);
        const n = note.properties();

        JSON.stringify({
            id: n.id,
            name: n.name,
            creationDate: n.creationDate,
            modificationDate: n.modificationDate
        });
    `);

    return JSON.parse(result) as Omit<Note, "body" | "plaintext">;
}

export async function getFolders(): Promise<Folder[]> {
    const result = await executeOSAScript(`
        const Notes = Application('Notes');
        const folders = Notes.folders();

        JSON.stringify(folders.map(folder => {
            const f = folder.properties();

            return {
                id: f.id,
                name: f.name
            };
        }));
    `);

    return JSON.parse(result) as Folder[];
}

export async function getNotes(
    folderId: string
): Promise<Omit<Note, "plaintext">[]> {
    const result = await executeOSAScript(`
        const Notes = Application('Notes');
        
        const targetFolder = Notes.folders.byId('${folderId}');
        const notes = targetFolder.notes();

        JSON.stringify(notes.map(n => {
            const p = n.properties();

            return {
                id: p.id,
                name: p.name,
                creationDate: p.creationDate,
                modificationDate: p.modificationDate,
            };
        }))
    `);

    const notes = JSON.parse(result);

    return notes as Omit<Note, "plaintext">[];
}

export async function getNoteById(id: string): Promise<Note> {
    const result = await executeOSAScript(`
        const Notes = Application('Notes');
        const note = Notes.notes.byId('${id}');

        const n = note.properties();

        JSON.stringify({
            id: n.id,
            name: n.name,
            plaintext: n.plaintext,
            creationDate: n.creationDate,
            modificationDate: n.modificationDate
        });
    `);

    return JSON.parse(result);
}

export async function getNoteByTitle(title: string): Promise<Note> {
    const result = await executeOSAScript(`
        const Notes = Application('Notes');
        
        const notes = Notes.notes.whose({name: '${title}'});        
        const note = notes[0];

        const n = note.properties();

        JSON.stringify({
            id: n.id,
            name: n.name,
            plaintext: n.plaintext,
            creationDate: n.creationDate,
            modificationDate: n.modificationDate
        });
    `);

    return JSON.parse(result);
}

export async function noteCount(): Promise<number> {
    const result = await executeOSAScript(`const Notes = Application('Notes');
const notes = Notes.notes();
notes.length`);

    return parseInt(result);
}
