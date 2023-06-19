from typing import TypeVar, Generic, cast

T = TypeVar('T')

class EasyQueue(Generic[T]):
    maxsize: int
    _list: list[T]
    _head: int
    _tail: int
    
    def __init__(self, maxsize: int) -> None:
        assert maxsize > 0
        self.maxsize = maxsize
        self._head = 0
        self._tail = -1
        self._list = []
        
    def __len__(self) -> int:
        if self._tail == -1:
            return 0
        return self._tail - self._head if self._tail > self._head else self._tail + self.maxsize - self._head
    
    def is_empty(self) -> bool:
        return len(self) == 0
    
    def is_full(self) -> bool:
        return len(self) == self.maxsize
        
    def put(self, value: T) -> T | None:
        idx = self._tail if self._tail != -1 else self._head
        if self.is_full():
            removed = self.head()
            self._head = (self._head + 1) % self.maxsize
        else:
            removed = None
        assert idx <= len(self._list)
        if idx == len(self._list):
            self._list.append(value)
        else:
            self._list[idx] = value
        self._tail = (idx + 1) % self.maxsize
        return removed
    
    def put_only(self, value: T) -> None:
        assert not self.is_full()
        self.put(value)
        
    def head(self) -> T | None:
        return None if self.is_empty() else self._list[self._head]
    
    def valid_head(self) -> T:
        assert not self.is_empty()
        result = self.head()
        return cast(T, result)
    
    def heads(self, n: int) -> list[T]:
        assert n >= 0
        n = min(n, len(self))
        return [self._list[i % self.maxsize] for i in range(self._head, self._head + n)]
    
    def tail(self) -> T | None:
        return None if self.is_empty() else self._list[self._tail - 1 if self._tail >= 1 else self._tail + self.maxsize - 1]
    
    def valid_tail(self) -> T:
        assert not self.is_empty()
        result = self.tail()
        return cast(T, result)
    
    def tails(self, n: int) -> list[T]:
        assert n >= 0
        n = min(n, len(self))
        return [self._list[i % self.maxsize] for i in range(self._tail + self.maxsize - n, self._tail + self.maxsize)]
    
    def list(self) -> list[T]:
        return self.heads(len(self))
    
    def poll(self) -> T | None:
        if self.is_empty():
            return None
        removed = self._list[self._head]
        self._head = (self._head + 1) % self.maxsize
        if self._head == self._tail:
            self._tail = -1
        return removed
    
    def valid_poll(self) -> T:
        assert not self.is_empty()
        result = self.poll()
        return cast(T, result)
     
    class Iterator:
        
        def __init__(self, q: "EasyQueue") -> None:
            self.q = q
            self.pos = 0
        
        def __iter__(self):
            self.pos = self.q._head
            return self
        
        def __next__(self) -> T:
            if self.pos == self.q._tail:
                raise StopIteration()
            value = self.q._list[self.pos]
            self.pos += 1
            if self.pos > self.q.maxsize:
                self.pos -= self.q.maxsize
            return value
        
    def __iter__(self) -> "Iterator":
        return self.Iterator(self)
    
if __name__ == "__main__":
    q: EasyQueue[int] = EasyQueue(3)
    assert len(q) == 0
    assert q.is_empty()
    assert not q.is_full()
    assert q.head() is None
    assert q.heads(0) == []
    assert q.heads(1) == []
    assert q.tail() is None
    assert q.tails(0) == []
    assert q.tails(1) == []
    removed = q.put(0)
    assert removed is None
    assert not q.is_empty()
    assert not q.is_full()
    assert len(q) == 1
    assert q.head() == 0
    assert q.heads(0) == []
    assert q.heads(1) == [0]
    assert q.heads(2) == [0]
    assert q.tail() == 0
    assert q.tails(0) == []
    assert q.tails(1) == [0]
    assert q.tails(2) == [0]
    removed = q.put(1)
    assert removed is None
    assert not q.is_empty()
    assert not q.is_full()
    assert len(q) == 2
    assert q.head() == 0
    assert q.heads(0) == []
    assert q.heads(1) == [0]
    assert q.heads(2) == [0, 1]
    assert q.heads(3) == [0, 1]
    assert q.tail() == 1
    assert q.tails(0) == []
    assert q.tails(1) == [1]
    assert q.tails(2) == [0, 1]
    assert q.tails(3) == [0, 1]
    removed = q.put(2)
    assert removed is None
    assert not q.is_empty()
    assert q.is_full()
    assert len(q) == 3
    assert q.head() == 0
    assert q.heads(0) == []
    assert q.heads(1) == [0]
    assert q.heads(2) == [0, 1]
    assert q.heads(3) == [0, 1, 2]
    assert q.heads(4) == [0, 1, 2]
    assert q.tail() == 2
    assert q.tails(0) == []
    assert q.tails(1) == [2]
    assert q.tails(2) == [1, 2]
    assert q.tails(3) == [0, 1, 2]
    assert q.tails(4) == [0, 1, 2]
    removed = q.put(3)
    assert removed == 0
    assert not q.is_empty()
    assert q.is_full()
    assert len(q) == 3
    assert q.head() == 1
    assert q.heads(0) == []
    assert q.heads(1) == [1]
    assert q.heads(2) == [1, 2]
    assert q.heads(3) == [1, 2, 3]
    assert q.heads(4) == [1, 2, 3]
    assert q.tail() == 3
    assert q.tails(0) == []
    assert q.tails(1) == [3]
    assert q.tails(2) == [2, 3]
    assert q.tails(3) == [1, 2, 3]
    assert q.tails(4) == [1, 2, 3]
    removed = q.poll()
    assert removed == 1
    assert not q.is_empty()
    assert not q.is_full()
    assert len(q) == 2
    assert q.head() == 2
    assert q.heads(0) == []
    assert q.heads(1) == [2]
    assert q.heads(2) == [2, 3]
    assert q.heads(3) == [2, 3]
    assert q.heads(4) == [2, 3]
    assert q.tail() == 3
    assert q.tails(0) == []
    assert q.tails(1) == [3]
    assert q.tails(2) == [2, 3]
    assert q.tails(3) == [2, 3]
    assert q.tails(4) == [2, 3]
    removed = q.poll()
    assert removed == 2
    assert not q.is_empty()
    assert not q.is_full()
    assert len(q) == 1
    assert q.head() == 3
    assert q.heads(0) == []
    assert q.heads(1) == [3]
    assert q.heads(2) == [3]
    assert q.heads(3) == [3]
    assert q.heads(4) == [3]
    assert q.tail() == 3
    assert q.tails(0) == []
    assert q.tails(1) == [3]
    assert q.tails(2) == [3]
    assert q.tails(3) == [3]
    assert q.tails(4) == [3]
    removed = q.poll()
    assert removed == 3
    assert q.is_empty()
    assert not q.is_full()
    assert len(q) == 0
    assert q.head() is None
    assert q.heads(0) == []
    assert q.heads(1) == []
    assert q.heads(2) == []
    assert q.heads(3) == []
    assert q.heads(4) == []
    assert q.tail() is None
    assert q.tails(0) == []
    assert q.tails(1) == []
    assert q.tails(2) == []
    assert q.tails(3) == []
    assert q.tails(4) == []
    removed = q.poll()
    assert removed is None
    assert q.is_empty()
    assert not q.is_full()
    assert len(q) == 0
    assert q.head() is None
    assert q.heads(0) == []
    assert q.heads(1) == []
    assert q.heads(2) == []
    assert q.heads(3) == []
    assert q.heads(4) == []
    assert q.tail() is None
    assert q.tails(0) == []
    assert q.tails(1) == []
    assert q.tails(2) == []
    assert q.tails(3) == []
    assert q.tails(4) == []  
    
            