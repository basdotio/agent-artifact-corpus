export interface FirestoreDocumentSnapshot<TDocument> {
  readonly id: string
  readonly exists: boolean
  data(): TDocument | undefined
}

export interface FirestoreDocumentRef<TDocument> {
  readonly path: string
  get(): Promise<FirestoreDocumentSnapshot<TDocument>>
  set(data: TDocument): Promise<void>
  update(data: Partial<TDocument>): Promise<void>
  delete(): Promise<void>
}

export interface FirestoreClient {
  doc<TDocument>(path: string): FirestoreDocumentRef<TDocument>
}

export interface FirestoreResource {
  readonly firestore: FirestoreClient
  readonly path: (id: string) => string
}

export async function getDocument<TDocument>(
  resource: FirestoreResource,
  id: string
) {
  const snapshot = await resource.firestore
    .doc<TDocument>(resource.path(id))
    .get()
  return snapshot.exists ? snapshot.data() : undefined
}

export async function setDocument<TDocument>(
  resource: FirestoreResource,
  id: string,
  data: TDocument
) {
  await resource.firestore.doc<TDocument>(resource.path(id)).set(data)
}

export async function updateDocument<TDocument>(
  resource: FirestoreResource,
  id: string,
  patch: Partial<TDocument>
) {
  await resource.firestore.doc<TDocument>(resource.path(id)).update(patch)
}

export async function deleteDocument<TDocument>(
  resource: FirestoreResource,
  id: string
) {
  await resource.firestore.doc<TDocument>(resource.path(id)).delete()
}

export interface FirestorePathFactory {
  readonly path: (id: string) => string
}

export function createFirestoreResource(
  firestore: FirestoreClient,
  path: FirestorePathFactory['path']
): FirestoreResource {
  return {
    firestore,
    path,
  }
}
