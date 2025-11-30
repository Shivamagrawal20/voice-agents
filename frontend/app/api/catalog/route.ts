import { NextResponse } from 'next/server';
import fs from 'node:fs/promises';
import path from 'node:path';

export const revalidate = 0;

export async function GET() {
  try {
    // frontend app runs from the frontend folder; shared-data is one level up
    const catalogPath = path.resolve(process.cwd(), '..', 'shared-data', 'day7_catalog.json');
    const file = await fs.readFile(catalogPath, 'utf-8');
    const data = JSON.parse(file);
    return NextResponse.json({ items: data });
  } catch (error) {
    console.error('Failed to load catalog', error);
    return NextResponse.json({ error: 'Unable to load catalog' }, { status: 500 });
  }
}





