import { MongoClient, ReadConcernLevel, Document } from "mongodb";

export async function runReadOnlyTransaction(client: MongoClient, collectionName: string, query: Document, limit?: number) {
    const session = client.startSession();
    try {
        // Start a transaction with readConcern set to 'snapshot'
        session.startTransaction({
            readConcern: { level: "snapshot" as ReadConcernLevel },
            readPreference: 'primary',
            writeConcern: { w: 1 }
        });

        const db = client.db();
        const collection = db.collection(collectionName);
        const docs = await collection.find(query, {
            session,
            limit
        }).toArray();

        // Commit the transaction (even though it's read-only)
        await session.commitTransaction();
        return docs;
    } catch (error) {
        console.error("Error during transaction:", error);
        if (session.inTransaction()) {
            await session.abortTransaction();
        }
        throw error;
    } finally {
        await session.endSession();
    }
}

export const getMongoClient = async (connectionString: string) => {
    const client = new MongoClient(connectionString, {
        monitorCommands: true,
    });
    try {
        await client.connect();
        console.log("Connected to MongoDB");
        return client;
    } catch (error) {
        console.error("Error connecting to MongoDB:", error);
        throw error;
    }
}
